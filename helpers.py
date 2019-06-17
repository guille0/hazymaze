import numpy as np
import cv2


def crop_from_points(img, corners, make_square=False):

    cnt = np.array([corners[0], corners[1], corners[2], corners[3]])

    rect = cv2.minAreaRect(cnt)
    center, size, theta = rect

    # Angle correction
    if theta < -45:
        theta += 90
        cnt = np.array([corners[1], corners[3], corners[0], corners[2]])

        rect = (center, size, theta)
        box = cv2.boxPoints(rect)
        box = np.int0(box)

        height = int(rect[1][0])
        width = int(rect[1][1])
    else:
        rect = (center, size, theta)
        box = cv2.boxPoints(rect)
        box = np.int0(box)

        height = int(rect[1][1])
        width = int(rect[1][0])

    src_pts = np.float32([corners[0],corners[1],corners[2],corners[3]])
    dst_pts = np.float32([[0,0],[width,0],[0,height],[width,height]])

    M = cv2.getPerspectiveTransform(src_pts, dst_pts)
    warped = cv2.warpPerspective(img, M, (width, height))

    transformation_data = {
        'matrix': M,
        'original_shape': (height, width)
    }

    return warped, transformation_data


def perspective_transform(img, transformation_matrix, original_shape=None, full_image_shape=(480,640)):

    h, w = full_image_shape[0], full_image_shape[1]

    warped = cv2.warpPerspective(img, transformation_matrix, (w, h))

    return warped


def blend_non_transparent(sprite, background_img):
    gray_overlay = cv2.cvtColor(background_img, cv2.COLOR_BGR2GRAY)
    overlay_mask = cv2.threshold(gray_overlay, 1, 255, cv2.THRESH_BINARY)[1]

    overlay_mask = cv2.erode(overlay_mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
    overlay_mask = cv2.blur(overlay_mask, (3, 3))

    background_mask = 255 - overlay_mask

    overlay_mask = cv2.cvtColor(overlay_mask, cv2.COLOR_GRAY2BGR)
    background_mask = cv2.cvtColor(background_mask, cv2.COLOR_GRAY2BGR)

    sprite_part = (sprite * (1 / 255.0)) * (background_mask * (1 / 255.0))
    overlay_part = (background_img * (1 / 255.0)) * (overlay_mask * (1 / 255.0))

    return np.uint8(cv2.addWeighted(sprite_part, 255.0, overlay_part, 255.0, 0.0))


def overlay_transparent(background, overlay, y, x):
    if y < 0:
        y = 0
    if x < 0:
        x = 0

    background_width = background.shape[1]
    background_height = background.shape[0]

    if x >= background_width or y >= background_height:
        return background

    h, w = overlay.shape[0], overlay.shape[1]

    if x + w > background_width:
        w = background_width - x
        overlay = overlay[:, :w]

    if y + h > background_height:
        h = background_height - y
        overlay = overlay[:h]

    if overlay.shape[2] < 4:
        overlay = np.concatenate(
            [
                overlay,
                np.ones((overlay.shape[0], overlay.shape[1], 1), dtype=overlay.dtype) * 255
            ],
            axis=2,
        )

    overlay_image = overlay[..., :3]
    mask = overlay[..., 3:] / 255.0

    background[y:y+h, x:x+w] = (1.0 - mask) * background[y:y+h, x:x+w] + mask * overlay_image

    return background


def resize_transparent_sprite(image, width=None, height=None, inter=cv2.INTER_AREA):
    # split image and alpha channel
    # resize them separately
    # join them
    other_channels = alpha_channel = image[:,:,:3]
    alpha_channel = image[:,:,3]

    dim = None
    (h, w) = image.shape[:2]

    # if both the width and height are None, then return the
    # original image
    if width is None and height is None:
        return image

    # check to see if the width is None
    if width is None:
        # calculate the ratio of the height and construct the
        # dimensions
        r = height / float(h)
        dim = (int(w * r), height)

    # otherwise, the height is None
    else:
        # calculate the ratio of the width and construct the
        # dimensions
        r = width / float(w)
        dim = (width, int(h * r))

    image_resized = cv2.resize(other_channels, dim, interpolation=inter)
    alpha_resized = cv2.resize(alpha_channel, dim, interpolation=inter)
    new_image = np.empty((dim[1], dim[0], 4))
    new_image[:, :, :3] = image_resized
    new_image[:, :, 3] = alpha_resized

    return new_image


class Singleton:
    """
    A non-thread-safe helper class to ease implementing singletons.
    This should be used as a decorator -- not a metaclass -- to the
    class that should be a singleton.

    The decorated class can define one `__init__` function that
    takes only the `self` argument. Also, the decorated class cannot be
    inherited from. Other than that, there are no restrictions that apply
    to the decorated class.

    To get the singleton instance, use the `instance` method. Trying
    to use `__call__` will result in a `TypeError` being raised.

    """

    def __init__(self, decorated):
        self._decorated = decorated

    def instance(self):
        """
        Returns the singleton instance. Upon its first call, it creates a
        new instance of the decorated class and calls its `__init__` method.
        On all subsequent calls, the already created instance is returned.

        """
        try:
            return self._instance
        except AttributeError:
            self._instance = self._decorated()
            return self._instance

    def __call__(self):
        raise TypeError('Singletons must be accessed through `instance()`.')

    def __instancecheck__(self, inst):
        return isinstance(inst, self._decorated)
