import numpy as np
import cv2


def load_slime():
    slime = cv2.imread('images/16x20slime.png', cv2.IMREAD_UNCHANGED)

    normal = np.empty((20, 16, 4, 4))

    slime_sprite = [normal]

    # Sliming (3 frames)
    # Dead (1 frame)

    for j, direction in enumerate(slime_sprite):
        for i in range(4):
            direction[:, :, :, i] = slime[j*20:j*20+20,i*16:i*16+16,:]

    return slime_sprite


def load_player():
    guy = cv2.imread('images/32x36guy.png', cv2.IMREAD_UNCHANGED)

    up = np.empty((36, 32, 4, 13))
    right = np.empty((36, 32, 4, 13))
    down = np.empty((36, 32, 4, 13))
    # make left out of flipping right
    left = np.empty((36, 32, 4, 13))

    player_sprite = [up, right, down]

    # Walking (3 frames)
    # Punching (4 frames)
    # Cheer (5 frames)
    # Dead (1 frame)

    for j, direction in enumerate(player_sprite):
        for i in range(13):
            direction[:, :, :, i] = guy[j*36:j*36+36,i*32:i*32+32,:]

    # Making left animation
    for i in range(13):
        rightframe = right[:,:,:, i]
        leftframe = cv2.flip(rightframe, 1)
        left[:,:,:,i] = leftframe

    player_sprite.append(left)

    return player_sprite


def load_doggy():
    dog = cv2.imread('images/32x32dog.png', cv2.IMREAD_UNCHANGED)

    left = np.empty((32, 32, 4, 7))
    up = np.empty((32, 32, 4, 7))
    down = np.empty((32, 32, 4, 7))
    # make right out of flipping left
    right = np.empty((32, 32, 4, 7))

    dog_sprite = [left, up, down]

    # 3 frames happy dog
    # 1 frame sleepy dog (only on left direction)

    for j, direction in enumerate(dog_sprite):
        for i in range(7):
            direction[:, :, :, i] = dog[j*32:j*32+32,i*32:i*32+32,:]

    # Making right animation
    for i in range(7):
        leftframe = left[:,:,:, i]
        rightframe = cv2.flip(leftframe, 1)
        right[:,:,:,i] = rightframe

    dog_sprite.append(right)

    return dog_sprite


def load_heart():
    heart = cv2.imread('images/16x16hearts.png', cv2.IMREAD_UNCHANGED)

    normal = np.empty((16, 16, 4, 3))

    heart_sprite = [normal]

    # Full, half heart (2 frames)

    for j, direction in enumerate(heart_sprite):
        for i in range(3):
            direction[:, :, :, i] = heart[j*16:j*16+16,i*16:i*16+16,:]

    return heart_sprite
