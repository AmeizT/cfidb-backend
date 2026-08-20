import tempfile


class ImagePreprocessor:
    def preprocess(self, uploaded_file):
        try:
            import cv2
            import numpy as np
            from PIL import Image, ImageOps
        except ImportError as exc:
            raise ValueError(
                "OCR image preprocessing dependencies are not installed. "
                "Install opencv-python-headless and pillow."
            ) from exc

        uploaded_file.seek(0)
        image = Image.open(uploaded_file)
        image = ImageOps.exif_transpose(image).convert("RGB")
        image_array = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

        gray = cv2.cvtColor(image_array, cv2.COLOR_BGR2GRAY)
        gray = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)

        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        contrasted = clahe.apply(gray)

        thresholded = cv2.adaptiveThreshold(
            contrasted,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            31,
            11,
        )

        corrected = self.correct_rotation(thresholded, cv2, np)

        temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        temp_file.close()
        cv2.imwrite(temp_file.name, corrected)

        uploaded_file.seek(0)
        return temp_file.name

    def correct_rotation(self, image, cv2, np):
        coords = np.column_stack(np.where(image < 255))

        if len(coords) < 10:
            return image

        angle = cv2.minAreaRect(coords)[-1]

        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle

        if abs(angle) < 0.5 or abs(angle) > 15:
            return image

        height, width = image.shape[:2]
        center = (width // 2, height // 2)
        matrix = cv2.getRotationMatrix2D(center, angle, 1.0)

        return cv2.warpAffine(
            image,
            matrix,
            (width, height),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE,
        )
