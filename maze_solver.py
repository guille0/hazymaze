from queue import PriorityQueue

import pickle


def astar(maze_object, start, destination, clear=True):
    # Quote for test
    q = PriorityQueue()
    start.distance = 0
    q.put((start.distance, start))

    while not q.empty():
        _, case = q.get()
        if case == destination:
            break
        for nextcase, path_distance in case.paths:
            if nextcase.back != case:
                if nextcase.distance > path_distance+case.distance:
                    nextcase.distance = path_distance+case.distance
                    nextcase.back = case
                    # q.put((path_distance, nextcase))
                    q.put((distance_to(nextcase, destination)+path_distance, nextcase))

    node = destination
    distance = destination.distance
    path = []
    while node.back:
        path.append(node)
        node = node.back
    path.append(node)

    # Resets all variables used in astar (Quote for test)
    if clear is True:
        maze_object.clear()
    return list(reversed(path)), distance


def distance_to(one, other):
    return abs(one.position[1]-other.position[1])+abs(one.position[0]-other.position[0])


# TESTING WITH PICKLED MAZE
if __name__ == '__main__':
    # test results:
    # [(0, 19), (3, 19), (3, 23), (7, 23), (7, 19), (9, 19), (9, 17), (11, 17), (13, 17),
    # (13, 21), (11, 21), (11, 23), (9, 23), (9, 25), (5, 25), (5, 29), (1, 29), (1, 33),
    # (3, 33), (3, 35), (1, 35), (1, 37), (3, 37), (5, 37), (5, 31), (7, 31), (7, 33),
    # (9, 33), (9, 39), (11, 39), (11, 37), (13, 37), (13, 39), (15, 39), (15, 33),
    # (13, 33), (13, 35), (11, 35), (11, 31), (17, 31), (19, 31), (19, 29), (21, 29),
    # (21, 31), (25, 31), (25, 29), (23, 29), (23, 27), (25, 27), (25, 25), (27, 25),
    # (27, 23), (25, 23), (25, 15), (23, 15), (21, 15), (19, 15), (19, 13), (13, 13),
    # (13, 9), (15, 9), (15, 11), (17, 11), (17, 7), (19, 7), (19, 9), (19, 11), (23, 11),
    # (23, 9), (27, 9), (27, 11), (25, 11), (25, 13), (31, 13), (31, 15), (27, 15), (27, 17),
    # (27, 21), (31, 21), (31, 17), (33, 17), (33, 13), (37, 13), (39, 13), (39, 15), (39, 21), (40, 21)]

    with open('pickled_maze', 'rb') as f:
        maze = pickle.load(f)

    # TEST ONLY
    # Get the entrance and the exit
    for case in maze.case_array[0]:
        if case != 0:
            if case.entrance is True:
                start = case
                break

    for case in maze.case_array[-1]:
        if case != 0:
            if case.entrance is True:
                destination = case
                break
    # END TEST ONLY

    # np.set_printoptions(threshold=np.inf)
    # print(maze.case_array)
    # print(start.position, destination.position)

    path = astar(maze.case_array, start, destination)
    print(path)
