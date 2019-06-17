import numpy as np
import cv2

from build_the_maze import Line


def find_maze(img):
    '''Finds the biggest object in the image and returns its 4 corners (to crop it)'''

    # Preprocessing:
    edges = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.GaussianBlur(edges, (11, 11), 0)
    edges = cv2.adaptiveThreshold(edges, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 19, 2)

    # cv2.imshow('adad', edges)

    # Get contours:
    contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    # Extracting the image of what we think might be a maze:
    if contours:

        conts = sorted(contours, key=cv2.contourArea, reverse=True)

        # Loops through the found objects
        # for something with at least 4 corners and kinda big (>5_000 pixels)
        for cnt in conts:

            epsilon = 0.025*cv2.arcLength(cnt, True)
            cnt = cv2.approxPolyDP(cnt, epsilon, True)

            if len(cnt) > 3:
                # Gets the 4 corners of the object (assume it's a square)
                topleft =       min(cnt, key=lambda x: x[0,0]+x[0,1])
                bottomright =   max(cnt, key=lambda x: x[0,0]+x[0,1])
                topright =      max(cnt, key=lambda x: x[0,0]-x[0,1])
                bottomleft =    min(cnt, key=lambda x: x[0,0]-x[0,1])
                corners = (topleft, topright, bottomleft, bottomright)

            else:
                # If it has less than 4 corners its not a maze
                return edges, None

            if cv2.contourArea(cnt) > 5000:
                rect = cv2.minAreaRect(cnt)
                box = cv2.boxPoints(rect)
                box = np.int0(box)
                # Returns the 4 corners of an object with 4+ corners and area of >10k
                return edges, corners

            else:
                return edges, None
    return edges, None


def find_items(maze_image):
    # Preprocessing to find the contour of the shapes
    h, w = maze_image.shape[0], maze_image.shape[1]
    dim = (h+w)//2
    b_and_w = cv2.cvtColor(maze_image, cv2.COLOR_BGR2GRAY)
    edges = cv2.GaussianBlur(b_and_w, (11, 11), 0)
    edges = cv2.adaptiveThreshold(edges, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 9, 2)

    cv2.rectangle(edges,(0, 0),(w-1,h-1),(255,255,255),16)
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    # cv2.imshow('d', edges)

    items = []

    if contours:
        item_mask = np.zeros(edges.shape, np.uint8)
        conts = sorted(contours, key=lambda x: cv2.contourArea(x), reverse=False)

        for cnt in conts:

            if cv2.contourArea(cnt) > 0.35*dim:
                return items, item_mask

            elif cv2.contourArea(cnt) > 0.05*dim:
                d = np.mean(cnt, axis=0)
                d[0][0], d[0][1] = int(round(d[0][0])), int(round(d[0][1]))

                # TODO adjust the size here?
                if cv2.contourArea(cnt) < 0.1*dim:
                    items.append((d, 'smol'))
                    cv2.drawContours(item_mask, [cnt], -1, (255,255,255), -1)
                else:
                    items.append((d, 'big'))
                    cv2.drawContours(item_mask, [cnt], -1, (255,255,255), -1)

    return items, item_mask


def find_lines(maze_image, item_mask=None):
    w, h = maze_image.shape[1], maze_image.shape[0]
    edges = cv2.cvtColor(maze_image, cv2.COLOR_BGR2GRAY)
    edges = cv2.GaussianBlur(edges, (11, 11), 0)
    # Make the 15 bigger if we're not getting some lines
    edges = cv2.adaptiveThreshold(edges, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 7, 2)
    if item_mask is not None:
        edges[item_mask > 0] = [0]

    cv2.rectangle(edges,(0, 0),(w-1,h-1),(0,0,0),15)

    # Getting vertical lines
    minLineLength = h/40
    maxLineGap = h/60
    vlines = cv2.HoughLinesP(edges, h, np.pi, threshold=0, minLineLength=minLineLength, maxLineGap=maxLineGap)

    # Flipping image and getting horizontal lines
    flipped_edges = cv2.rotate(edges, cv2.ROTATE_90_COUNTERCLOCKWISE)
    flipped_edges = cv2.flip(flipped_edges, 0)
    minLineLength = flipped_edges.shape[0]/40
    maxLineGap = flipped_edges.shape[0]/60
    hlines = cv2.HoughLinesP(flipped_edges, w, np.pi, threshold=0, minLineLength=minLineLength, maxLineGap=maxLineGap)

    # 2 is fine. Even 1 is fine but 2 just in case
    line_thickness = 2

    def group_lines(lines, direction):
        if lines is None:
            return None
        else:
            lines = sorted(lines, key=lambda k: k[0][0])
            # Turn all vertical lines with similar X into one
            # Turn all horizontal lines with similar Y into one
            maze_lines = []
            prevx = lines[0][0][0]
            exes = []
            if direction == 'v':
                array = np.zeros((h), dtype=np.bool)
            else:
                array = np.zeros((flipped_edges.shape[0]), dtype=np.bool)

            for line in lines:
                x, y1, x2, y2 = line[0]
                if x-prevx < line_thickness:
                    array[y2:y1] = True
                    exes.append(x)
                else:
                    maze_lines.append(Line(array, int(round(np.mean(exes))), direction))
                    # Reset line
                    if direction == 'v':
                        array = np.zeros((h), dtype=np.bool)
                    else:
                        array = np.zeros((flipped_edges.shape[0]), dtype=np.bool)
                    exes = []
                    # Add to it
                    array[y2:y1] = True
                    exes.append(x)
                prevx = x
            else:
                # When we are done, remember to append the last line
                maze_lines.append(Line(array, int(round(np.mean(exes))), direction))

        return maze_lines

    maze_vlines = group_lines(vlines, 'v')
    maze_hlines = group_lines(hlines, 'h')

    # cv2.imshow('ededed', maze_image)

    if maze_vlines is None or maze_hlines is None:
        return None, None
    else:
        return maze_vlines, maze_hlines
