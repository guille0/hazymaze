import numpy as np
import cv2
import pickle

from maze_solver import astar
from game import Master


class Maze:
    def __init__(self, vlines, hlines):
        self.vlines = vlines
        self.hlines = hlines
        self.items = []
        self.entrances = []
        self.maze_array = np.array([])

    def is_valid(self):
        # If it has less than 2 entrances, it's invalid
        if len(self.entrances) < 2:
            print(f'{len(self.entrances)} found, requires at least 2')
            return False

        # If finding path from entrance to exit gives an error or there is no path, it's invalid
        path = self.test_path()
        if len(path) < 2:
            print('No path found from entrance to exit. Bad map?')
            return False
        else:
            for prevcase, case in zip(path, path[1:]):
                py, px = self.real_position(prevcase.position[0], prevcase.position[1])
                y, x = self.real_position(case.position[0], case.position[1])
                if None in (py, px, y, x):
                    np.set_printoptions(threshold=np.inf)
                    print(self.maze_array)
                    print(f'''Positions of some of the cases in the path
                    from entrance to exit seem incorrect. Bad map?
                    prevcase: {(prevcase.position[0], prevcase.position[1])}
                    case: {(case.position[0], case.position[1])}
                    py, px, y, x: {(py, px, y, x)}''')

                    return False

        return True

    def real_position(self, y, x):
        '''Returns y and x values for coordinates in the maze
           Returns None, None if they are outside the maze'''
        try:
            if y % 2 == 0:
                realy = self.hlines[y//2].position
            else:
                realy = self.ygrid[y//2]
            if x % 2 == 0:
                realx = self.vlines[x//2].position
            else:
                realx = self.xgrid[x//2]

        except IndexError:
            # print(f'real_position out of range: {y, x}')
            return None, None

        return realy, realx

    def get_walkable_grid(self):
        # Lists of x and y positions for the grid
        self.xgrid = []
        self.ygrid = []
        for vline, nextvline in zip(self.vlines, self.vlines[1:]):
            x = int(round((vline.position+nextvline.position)/2))
            self.xgrid.append(x)
        for hline, nexthline in zip(self.hlines, self.hlines[1:]):
            y = int(round((hline.position+nexthline.position)/2))
            self.ygrid.append(y)

    def build_items(self, items):
        for [[x, y]], kind in items:
            if x > self.vlines[0].position and x < self.vlines[-1].position:
                if y > self.hlines[0].position and y < self.hlines[-1].position:
                    # Gets the closest position to its y, x in the grid
                    y = self.ygrid.index(min(self.ygrid, key=lambda k: abs(y-k)))
                    x = self.xgrid.index(min(self.xgrid, key=lambda k: abs(x-k)))
                    y = y*2+1
                    x = x*2+1

                    if y < self.maze_array.shape[0] and x < self.maze_array.shape[1]:
                        self.items.append(((y,x), kind))
                        if kind == 'smol':
                            self.maze_array[y,x] = 9
                        else:
                            self.maze_array[y,x] = 7

    def build_maze(self, items, key=None):
        game = Master.instance()

        # Making a binary maze (1 is wall 0 is walkable)
        self.build_basic_maze()
        self.build_items(items)

        # Turn out binary maze into a string
        # Save it in a dictionary that points to the finished maze (self.case_array)
        # So if we are trying to build the same maze, we don't have to recreate it
        np.set_printoptions(threshold=np.inf)
        binary_maze_string = np.array2string(self.maze_array)

        if binary_maze_string in game.built_mazes.keys():
            self.case_array, self.entrances, self.items = game.built_mazes[binary_maze_string]
        else:
            self.compress_maze(items)
            game.built_mazes[binary_maze_string] = (self.case_array, self.entrances, self.items)

        if key is not None:
            if key == ord('q'):
                print(binary_maze_string)
                for e in self.entrances:
                    print(self.real_position(e[0], e[1]))
                print(self.entrances)
                print(self.items)

    def build_basic_maze(self):
        height = len(self.ygrid)+len(self.hlines)
        width = len(self.xgrid)+len(self.vlines)
        maze_array = np.zeros((height, width), dtype=np.uint8)

        # print(len(self.hlines))
        for i in range(height):
            if i % 2 == 0:
                maze_array[i, :] = 1

        for i in range(width):
            if i % 2 == 0:
                maze_array[:, i] = 1

        # for each xgrid, check all the vlines
        # for each ygrif, check all the hlines
        for i, x in enumerate(self.xgrid):
            for j, hline in enumerate(self.hlines):
                if hline.array[x] == 0:
                    maze_array[j*2,i*2+1] = 0
        for i, y in enumerate(self.ygrid):
            for j, vline in enumerate(self.vlines):
                # print(vline.array[y])
                if vline.array[y] == 0:
                    maze_array[i*2+1,j*2] = 0

        self.maze_array = maze_array
        # np.set_printoptions(threshold=np.inf)
        # print(maze_array)

        return maze_array

    def compress_maze(self, items):
        # Turn all the 0s into Case objects and add their paths
        # Afterwards we can loop through those paths and remove corridors
        h = self.maze_array.shape[0]-1
        w = self.maze_array.shape[1]-1
        self.case_array = np.zeros_like(self.maze_array, dtype=np.object)

        # Look for entrances in y=0, y=h, x=0, x=w
        def get_entrances():
            entrances = []
            for x, case in enumerate(self.maze_array[0, :]):
                if case == 0:
                    entrances.append((0,x))
            for x, case in enumerate(self.maze_array[h, :]):
                if case == 0:
                    entrances.append((h,x))
            for y, case in enumerate(self.maze_array[:, 0]):
                if case == 0:
                    entrances.append((y,0))
            for y, case in enumerate(self.maze_array[:, w]):
                if case == 0:
                    entrances.append((y,w))
            return entrances

        def nearby_squares(y, x):
            paths = []
            corridor = False
            verts = 0
            hors = 0
            if y > 0:
                if self.maze_array[y-1, x] != 1:
                    verts += 1
                    paths.append((y-1, x))
            if y < h:
                if self.maze_array[y+1, x] != 1:
                    verts += 1
                    paths.append((y+1, x))
            if x > 0:
                if self.maze_array[y, x-1] != 1:
                    hors += 1
                    paths.append((y, x-1))
            if x < w:
                if self.maze_array[y, x+1] != 1:
                    hors += 1
                    paths.append((y, x+1))

            if (hors == 2 and verts == 0) or (verts == 2 and hors == 0):
                corridor = True

            return paths, corridor

        self.entrances = get_entrances()

        if not self.entrances:
            return None

        non_Cs = []

        for y, row in enumerate(self.maze_array):
            for x, case in enumerate(row):
                value = case
                if value != 1:
                    self.case_array[y,x] = Case(value, (y,x))
                    nearbys, corridor = nearby_squares(y, x)
                    # Because items are not corridors
                    if value == 0:
                        self.case_array[y,x].corridor = corridor
                    if self.case_array[y,x].corridor is False:
                        non_Cs.append(self.case_array[y,x])
                        # Get its nearby squares
                    [self.case_array[y,x].add_nearby_square(nearby) for nearby in nearbys]

        for entrance in self.entrances:
            self.case_array[entrance].entrance = True

        # We got an array where walkable places are Case objects
        # corridors have case.corridor = True
        # and they also have each a list of their nearby squares

        def get_to_non_c(prevcase, currentpos):
            currentcase = self.case_array[currentpos]
            distance = 1
            while currentcase.corridor is True:
                distance += 1
                # if it's a corridor, just look in its path that isn't (prev.y, prev.x)
                # counter = 0
                for nearby in currentcase.nearby_squares:
                    # counter +=1
                    if nearby == (prevcase.position[0], prevcase.position[1]):
                        continue
                    else:
                        break
                # print(f'looped {counter} times, shoudl have looped {len(currentcase.nearby_squares)} times')
                # nearby is the (y, x) of the next square we wanna go to
                prevcase = currentcase
                currentcase = self.case_array[nearby]

            return currentcase, distance

        # So now we craate paths between all the non-Cs and check their distances
        for dude in non_Cs:
            # check for all its nearby squares, when we reach a non-corridor, set our path to it & distance
            for nearby in dude.nearby_squares:
                non_c, distance = get_to_non_c(dude, nearby)
                dude.add_path(non_c, distance)

        self.non_Cs = non_Cs

    # For testing
    def pickle(self):
        with open('pickled_maze', 'wb') as f:
            pickle.dump(self, f)

    def test_path(self):
        start = self.case_array[self.entrances[0]]
        end = self.case_array[self.entrances[1]]
        try:
            path, distance = astar(self, start, end)
        except AttributeError as e:
            print(e)
            return []
        return path

    def clear(self):
        'Resets variables used for astar algorithm'
        for y, row in enumerate(self.case_array):
            for x, case in enumerate(row):
                if isinstance(case, Case):
                    case.clear()

    def draw_path(self, path, image):
        for prevcase, case in zip(path, path[1:]):
            py, px = self.real_position(prevcase.position[0], prevcase.position[1])
            y, x = self.real_position(case.position[0], case.position[1])
            if None not in (py, px, y, x):
                cv2.line(image, (px, py), (x, y), (255,0,0), 1)
            else:
                print('path not found (draw path)')

    def draw_grid(self, image):
        for x in self.xgrid:
            cv2.line(image, (x, 0), (x, 400), (255,0,0), 1)
        for y in self.ygrid:
            cv2.line(image, (0, y), (400, y), (0,255,0), 1)

    def draw_maze(self, image):
        'requires live feed'
        for vline in self.vlines:
            vline.draw_line(image)
        for hline in self.hlines:
            hline.draw_line(image)

    def draw_items(self, image):
        for item in self.items:
            y, x = self.real_position(item[0][0], item[0][1])
            if None not in (y, x):
                if item[1] == 'smol':
                    cv2.circle(image, (x, y), 2, (255, 0, 0), thickness=-1, lineType=8, shift=0)
                else:
                    cv2.circle(image, (x, y), 2, (0, 255, 0), thickness=-1, lineType=8, shift=0)


class Line:
    def __init__(self, array, position, kind):
        self.array = array
        self.position = position
        self.kind = kind

    def __repr__(self):
        return str(self.position)

    def draw_line(self, image):
        mask = np.zeros(shape=(image.shape[0], image.shape[1]))
        if self.kind == 'v':
            mask[:, self.position] = self.array
            image[mask == True] = (0, 0, 255)
        if self.kind == 'h':
            mask[self.position, :] = self.array
            image[mask == True] = (0, 0, 255)


class Case:
    def __init__(self, value, position):
        self.value = value
        self.position = position
        self.corridor = False
        self.entrance = False
        self.paths = []
        self.nearby_squares = []

        # for A*
        self.distance = np.inf
        self.back = None

    def __repr__(self):
        # return str(self.position)
        if not self.paths:
            return '?'
        if self.value > 1:
            return 'H'
        if self.entrance:
            return 'E'
        if self.corridor:
            return '='
        else:
            return '1'

    def __lt__(self, other):
        return True

    def clear(self):
        self.distance = np.inf
        self.back = None

    def add_path(self, case, distance):
        self.paths.append((case, distance))

    def add_nearby_square(self, pos):
        self.nearby_squares.append(pos)
