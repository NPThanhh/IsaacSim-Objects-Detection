import rclpy
from rclpy.node import Node

from sensor_msgs.msg import Image
from cv_bridge import CvBridge

from ultralytics import RTDETR


class RTDETRNode(Node):

    def __init__(self):
        super().__init__('rtdetr_node')

        # =========================
        # CV Bridge
        # =========================
        self.bridge = CvBridge()

        # =========================
        # Load RT-DETR model
        # =========================
        self.model = RTDETR(
            "/home/npthanh/IsaacSim-Objects-Detection/models/best.pt"
        )

        # =========================
        # Subscribe RGB camera
        # =========================
        self.subscription = self.create_subscription(
            Image,
            '/rgb',
            self.image_callback,
            10
        )

        # =========================
        # Publish visualized image
        # =========================
        self.image_pub = self.create_publisher(
            Image,
            '/detection/image',
            10
        )

        self.get_logger().info(
            "RT-DETR node started"
        )

    def image_callback(self, msg):

        try:

            # =========================
            # 1. ROS Image -> OpenCV
            # =========================

            frame = self.bridge.imgmsg_to_cv2(
                msg,
                desired_encoding='bgr8'
            )

            # =========================
            # 2. RT-DETR inference
            # =========================

            results = self.model(
                frame,
                verbose=False
            )

            result = results[0]

            # =========================
            # 3. Get detections
            # =========================

            boxes = result.boxes

            for box in boxes:

                x1, y1, x2, y2 = (
                    box.xyxy[0]
                    .cpu()
                    .numpy()
                )

                confidence = float(
                    box.conf[0]
                )

                class_id = int(
                    box.cls[0]
                )

                class_name = (
                    self.model.names[class_id]
                )

                self.get_logger().info(
                    f"{class_name}: "
                    f"{confidence:.2f} "
                    f"box=("
                    f"{x1:.0f}, "
                    f"{y1:.0f}, "
                    f"{x2:.0f}, "
                    f"{y2:.0f})"
                )

            # =========================
            # 4. Draw bounding boxes
            # =========================

            annotated = result.plot()

            self.get_logger().info(
                f"Annotated image: "
                f"shape={annotated.shape}, "
                f"dtype={annotated.dtype}"
            )

            # =========================
            # 5. OpenCV -> ROS Image
            #    Không dùng cv2_to_imgmsg()
            # =========================

            output_msg = Image()

            output_msg.header = msg.header

            output_msg.height = annotated.shape[0]
            output_msg.width = annotated.shape[1]

            output_msg.encoding = 'bgr8'
            output_msg.is_bigendian = 0

            output_msg.step = annotated.strides[0]

            output_msg.data = annotated.tobytes()

            # =========================
            # 6. Publish
            # =========================

            self.image_pub.publish(output_msg)

        except Exception as e:

            self.get_logger().error(
                f"Error processing image: "
                f"{repr(e)}"
            )


def main(args=None):

    rclpy.init(args=args)

    node = RTDETRNode()

    try:
        rclpy.spin(node)

    except KeyboardInterrupt:
        pass

    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
