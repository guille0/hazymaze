import numpy as np
import cv2

from helpers import crop_from_points, perspective_transform, blend_non_transparent
from extract_lines import find_lines, find_maze, find_items
from build_the_maze import Maze
from game import Master

from datetime import datetime


# MAIN
def maze_boi(img_original, key):
    first = datetime.now()
    game = Master.instance()

    # Tries to find the part of the image with the maze
    img_test, corners = find_maze(img_original)

    # If we need to find a maze (when paused, we look for the maze we were on before)
    # Grabbing maze image and creating maze
    if game.playing is False or game.pause is True:
        # If we got an object (maybe maze?)
        if corners is not None:
            # We crop out the maze and get the info needed to paste it back (matrix)
            img_cropped_maze, transformation = crop_from_points(img_original, corners)
            # cv2.imshow('asdasdasdasd', img_cropped_maze)
            # with img_cropped_maze get the red bits and extract them (mask)
            transformation_matrix = transformation['matrix']
            original_shape = transformation['original_shape']

            # We inverse the matrix so we can do the opposite transformation later
            transformation_matrix = np.linalg.pinv(transformation_matrix)

            items, item_mask = find_items(img_cropped_maze)

            vlines, hlines = find_lines(img_cropped_maze, item_mask)

            if vlines and hlines:
                maze = Maze(vlines, hlines)
                maze.get_walkable_grid()

                # Visuals
                # maze.draw_grid(img_cropped_maze)
                # maze.draw_lines(img_cropped_maze)
                maze.draw_maze(img_cropped_maze)

                # Turn the maze into an array we can work with
                maze.build_maze(items, key=key)
                # img_cropped_maze[item_mask > 0] = (180, 255, 0)
                maze.draw_items(img_cropped_maze)

                if maze.is_valid() is not True:
                    return img_original
                else:

                    if game.pause is True:
                        # When it finds it, it just returns to it
                        if np.array2string(maze.maze_array) == np.array2string(game.maze.maze_array):
                            game.pause = False

                    if game.playing is False:
                        game.ready = True
                        h, w = img_cropped_maze.shape[0], img_cropped_maze.shape[1]
                        # Ready to play, listen to key press
                        if key == game.key:
                            game.dump_maze(maze, h, w)
                            game.start()
                            key = -1    # So we don't trigger another keypress

            else:
                return img_original

    # Playing the game
    if game.playing is True and game.pause is False:
        if corners is not None:
            img_cropped_maze, transformation = crop_from_points(img_original, corners)
            transformation_matrix = transformation['matrix']
            original_shape = transformation['original_shape']
            transformation_matrix = np.linalg.pinv(transformation_matrix)
            # first = datetime.now()
            maze = game.maze
            h, w = img_cropped_maze.shape[0], img_cropped_maze.shape[1]
            game.adjust_lines(h, w)
            # maze.draw_grid(img_cropped_maze)
            game.step(img_cropped_maze)
            # print(f'time-taken: {datetime.now()-first}')
            # maze.draw_items(img_cropped_maze)

        elif corners is None:
            # If no object was found we have to look for the same maze again
            # When we got it, it will unpause.
            game.pause = True

    # Exit button (unloads the maze)
    if game.playing is True:
        if key == game.key:
            game.stop()
            key = -1    # So we don't trigger another keypress

    # Pasting cropped maze into full image
    if corners is not None:
        # We paste the cropped maze which is now solved into the camera image
        # TODO HIDE?: Test texts:
        # if game.pause is True:
        #     write_text(img_original, 'Paused')
        # if game.playing is True:
        #     write_text(img_original, 'Playing')
        # if game.ready is True:
        #     write_text(img_original, 'Press space to begin!')
        #     game.ready = False
        # cv2.imshow('cropped', img_cropped_maze)
        img_maze_final = perspective_transform(img_cropped_maze, transformation_matrix,
                                               original_shape, img_original.shape)
        img_final = blend_non_transparent(img_original, img_maze_final)

    else:
        # If we found no maze, return same image
        img_final = img_original

    # print(f'time-taken: {datetime.now()-first}')
    return img_final


def write_text(image, text):
    h, w = image.shape[0], image.shape[1]
    font = cv2.FONT_HERSHEY_DUPLEX
    cv2.putText(image,text, (w//5, h-40), font, 1,(255,255,255),2,cv2.LINE_AA)
