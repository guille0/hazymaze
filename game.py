from helpers import Singleton, overlay_transparent, resize_transparent_sprite
from maze_solver import astar
from load_images import load_player, load_slime, load_doggy, load_heart

import numpy as np
from math import log

from time import perf_counter


@Singleton
class Master:
    def __init__(self):
        # Loading sprites
        self.player_sprite = load_player()
        self.slime_sprite = load_slime()
        self.dog_sprite = load_doggy()
        self.heart_sprite = load_heart()

        self.key = 32           # Spacebar
        self.playing = False
        self.pause = False
        self.ready = False      # Whether we have a valid maze image
        self.maze = None        # Loaded Maze object
        self.original_height = None
        self.original_width = None

        self.original_vlines = []
        self.original_hlines = []
        self.original_xgrid = []
        self.original_ygrid = []

        self.built_mazes = dict()

        self.units = []
        self.ignored_entrances = []
        self.cheering_dogs = []

    def get_min_dimension(self):
        'Gets the minimum height/width of the smallest square in the grid, for resizing sprites'
        min_dimension = np.inf
        for vline, nextvline in zip(self.maze.vlines, self.maze.vlines[1:]):
            min_dimension = min(min_dimension, nextvline.position - vline.position)
        for hline, nexthline in zip(self.maze.hlines, self.maze.hlines[1:]):
            min_dimension = min(min_dimension, nexthline.position - hline.position)
        return min_dimension

    def step(self, img_cropped_maze):
        t = perf_counter()

        # We calculate the smallest case there is and make the units a size that fits it
        min_dimension = self.get_min_dimension()

        # Do actions for each unit
        if self.player.action not in ['cheering', 'dead']:
            self.player.step(min_dimension)
            for npc in self.enemies + self.dogs:
                npc.step(min_dimension)
        # Dogs can still walk out even after the player finished the map
        for dog in self.cheering_dogs:
            dog.step(min_dimension)

        # print(f'passed {perf_counter()-t}')
        t = perf_counter()

        # Draw each unit (player has priority so draw him last)
        for enemy in self.enemies:
            enemy.draw(img_cropped_maze, sprite_height=min_dimension)
        for dog in self.dogs + self.cheering_dogs:
            dog.draw(img_cropped_maze, sprite_height=int(round(min_dimension*1.25)))
        self.player.draw(img_cropped_maze, sprite_height=int(round(min_dimension*1.8)))

        # print(f'drawing {perf_counter()-t}')
        t = perf_counter()

    def start(self):
        'Only do this one, time, when starting a new maze for the first time'
        # Create Player, Enemies, Items, set entrances

        # Figure out size of the grid so we can calculate speed better
        min_dimension = self.get_min_dimension()

        self.speed_multiplier = 1 + log(min_dimension, 400)

        # Append to ignored_entrances so he doesn't walk out the way he came in
        entrance = self.maze.entrances[0]
        self.ignored_entrances.append(entrance)

        self.player = Player(y=entrance[0], x=entrance[1], sprite=self.player_sprite, game=self)

        # Creates enemies and dogs
        self.dogs = []
        self.enemies = []
        for item in self.maze.items:
            if item[1] == 'smol':
                enemy = Enemy(item[0][0], item[0][1], self.slime_sprite, self)
                enemy.set_patrol()
                self.enemies.append(enemy)
            else:
                dog = Item(item[0][0], item[0][1], self.dog_sprite, self)
                self.dogs.append(dog)

        self.playing = True
        print('Started, created units')

    def stop(self):
        'Stops and forgets the maze'
        self.pause = False
        self.playing = False
        self.maze = None
        self.units = []
        self.ignored_entrances = []
        self.cheering_dogs = []
        print('Stopped')

    def dump_maze(self, maze, h, w):
        self.maze = maze
        self.original_height = h
        self.original_width = w
        self.original_vlines = [line.position for line in maze.vlines]
        self.original_hlines = [line.position for line in maze.hlines]
        self.original_xgrid = maze.xgrid
        self.original_ygrid = maze.ygrid

    def adjust_lines(self, h, w):
        'Since lines can change position when the maze is moved, we have to keep adjusting them'
        h_proportion = h/self.original_height
        w_proportion = w/self.original_width

        for i, line in enumerate(self.original_vlines):
            self.maze.vlines[i].position = int(round(line*w_proportion))
        for i, line in enumerate(self.original_hlines):
            self.maze.hlines[i].position = int(round(line*h_proportion))

        new_xgrid = [int(round(line*w_proportion)) for line in self.original_xgrid]
        new_ygrid = [int(round(line*h_proportion)) for line in self.original_ygrid]

        self.maze.xgrid = new_xgrid
        self.maze.ygrid = new_ygrid


class Unit:
    def __init__(self, y, x, sprite, game):
        self.game = game
        self.maze = game.maze
        self.spawn = self.maze.case_array[y,x]
        self.array_y = y
        self.array_x = x
        # actions = ['walking', 'cheering', 'standing', 'fighting']
        self.action = 'walking'
        self.sprite = sprite
        self.first_frame = 0
        self.last_frame = 3
        self.current_frame = 0
        # Animation speed (1 = one image per frame)
        self.image_speed = 1
        # 0 = right, 1 = up, 2 = left, 3 = down
        self.direction = 3

    def real_position(self):
        first_y, first_x = self.maze.real_position(self.array_y, self.array_x)

        if self.moving_to is None:
            y, x = first_y, first_x
        else:
            second_y, second_x = self.maze.real_position(self.moving_to.position[0], self.moving_to.position[1])

            if self.moving_to.position[0] == self.array_y:
                # we move horizontally
                x_distance = abs(first_x-second_x)
                x = int(round(first_x+(self.relative_x*x_distance)))
                y = first_y
            elif self.moving_to.position[1] == self.array_x:
                # we move vertically
                y_distance = abs(first_y-second_y)
                y = int(round(first_y+(self.relative_y*y_distance)))
                x = first_x
            else:
                # IGNORE
                print('Path error! Maze loaded incorrectly?')
                print(f'moving from {self.array_y}, {self.array_x} to {self.moving_to.position}')
        return y, x

    def real_distance(self, other):
        other_y, other_x = other.real_position()
        y, x = self.real_position()
        a = np.array([other_y, other_x])
        b = np.array([y, x])
        dist = np.linalg.norm(a-b)
        return dist


class Mover(Unit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # For movement between cases
        self.relative_y = 0
        self.relative_x = 0

        self.moving_to = None
        self.path = []
        self.fighting = []

    def remove_fight(self, other):
        self.fighting.remove(other)
        if not self.fighting:
            if self.action != 'dead':
                self.action = 'walking'

    def add_fight(self, other):
        if other not in self.fighting:
            self.fighting.append(other)

    def change_hp(self, amount):
        self.hp += amount
        if self.hp <= 0:
            self.action = 'dead'
        if self.hp > self.max_hp:
            self.hp = self.max_hp

    def make_path(self, goal, start=None):
        'Makes self.path into a list of steps from the object to the goal'
        if start is None:
            start = self.maze.case_array[self.array_y, self.array_x]
        path, distance = astar(self.maze, start, goal)
        return path, distance

    def set_path(self, path_tuple):
        path, distance = path_tuple
        self.path = list(reversed(path))

    def step(self, min_dimension):
        if self.action in ['chasing', 'walking']:
            self.moving()
        self.class_step(min_dimension)

    def moving(self):
        'Following self.path (path to destination) and self.moving_to (next position)'
        # Standing still
        if self.moving_to is None:
            # If we have a path, start following it until it's done
            if self.path:
                self.moving_to = self.path.pop()

        # Moving
        if self.moving_to is not None:
            # Get the position of the Case we want to move to
            y2, x2 = self.moving_to.position
            # Calculate distance to it (it will always be either a horizontal or vertical move)
            x_distance = x2-self.array_x
            y_distance = y2-self.array_y

            # If it's already where it wants to go
            if y_distance == 0 and x_distance == 0:
                self.array_y, self.array_x = y2, x2
                self.relative_y, self.relative_x = 0, 0
                self.moving_to = None
                self.moving()

            elif y_distance == 0:
                self.relative_x += self.move_speed/x_distance
                self.direction = 0 if self.array_x < x2 else 2

            elif x_distance == 0:
                self.relative_y += self.move_speed/y_distance
                self.direction = 3 if self.array_y < y2 else 1
            else:
                print('Can\'t do diagonal moves!!')

            if abs(self.relative_x)+abs(self.relative_y) >= 1:
                self.array_y, self.array_x = y2, x2
                self.relative_y, self.relative_x = 0, 0
                self.moving_to = None
                self.moving()

            if self.moving_to is None:
                # If we just reached our destination look for the next one on the path
                if self.path:
                    self.moving_to = self.path.pop()


class Player(Mover):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_hp = 300
        self.hp = self.max_hp
        self.attack_power = 2
        # The number of hearts that appear on top of his head to show remaining HP
        self.hearts_shown = 3
        # Whether the Guy finished everything they had to do
        self.finished = False
        # NOTE: Change this for showing hearts for longer
        self.show_hp_max_timer = 20
        self.show_hp_timer = 0
        # NOTE: Change this for speed
        self.move_speed = 0.5 / self.game.speed_multiplier
        self.image_speed = self.move_speed*2

    def change_hp(self, *args, **kwargs):
        super().change_hp(*args, **kwargs)
        self.show_hp_timer = self.show_hp_max_timer

    def action_dog_collision(self):
        if self.game.maze.case_array[self.array_y, self.array_x].value == 7:
            for dog in self.game.dogs:
                if dog.array_y == self.array_y and dog.array_x == self.array_x:
                    self.change_hp(50)
                    # Put dog in barking mode and activate the timer until he runs out
                    dog.action = 'cheering'
                    dog.cheer_timer = dog.max_cheer_timer
                    self.game.cheering_dogs.append(dog)
                    self.game.dogs.remove(dog)
                    # Make it so he faces the player
                    if self.direction == 0:
                        dog.direction = 2
                    elif self.direction == 1:
                        dog.direction = 3
                    elif self.direction == 2:
                        dog.direction = 0
                    elif self.direction == 3:
                        dog.direction = 1

                    self.path = None
                    self.moving_to = None

    def action_find_path(self):
        '1: find all possible dogs, 2: leave the maze'
        # If our guy isn't doing anything, get him going
        if not self.path and self.action not in ['cheering', 'fighting']:
            shortest_path = ([], np.inf)
            # 1st priority is dogs, 2nd is leaving the maze
            if self.game.dogs:
                for dog in self.game.dogs:
                    # Since dogs don't move, we go for their spawn Case
                    path, distance = self.make_path(dog.spawn)
                    if distance < shortest_path[1]:
                        shortest_path = (path, distance)
                # If there is a path, get our guy on the way
                if shortest_path[1] != np.inf:
                    self.set_path(shortest_path)

            # If there AREN'T dogs left or if we could not find a path to them, we leave
            if not self.game.dogs or not self.path:
                self.finished = True
                shortest_path = ([], np.inf)

                for entrance_coords in self.game.maze.entrances:
                    if entrance_coords not in self.game.ignored_entrances:
                        # Find shortest path to exit (exluding the one we came from, which we popped)
                        goal = self.game.maze.case_array[entrance_coords]
                        path, distance = self.make_path(goal)
                        # Keep the shortest path to a dougie
                        if distance < shortest_path[1]:
                            shortest_path = (path, distance)
                # If we found is a path, follow it
                if shortest_path[1] != np.inf:
                    self.set_path(shortest_path)
                else:
                    # This should never happen unless you edit with the maze in the middle of it
                    print('error exit not found?')

    def class_step(self, min_dimension=None):
        # Timer for showing hearts on top of his lil head
        if self.show_hp_timer > 0:
            self.show_hp_timer -= 1

        self.action_dog_collision()
        self.action_find_path()

        # If we are at the exit (and we have rescued all rescuable dogs), its over
        if self.finished is True:
            if self.game.maze.case_array[self.array_y, self.array_x].entrance is True:
                if (self.array_y, self.array_x) not in self.game.ignored_entrances:
                    self.action = 'cheering'
                    self.direction = 3
                    self.path = None
                    self.moving_to = None

    def draw(self, image, sprite_height):
        sprite, first_frame, last_frame = self.get_sprite(self.direction)

        self.current_frame += self.image_speed

        if self.current_frame < first_frame or self.current_frame >= last_frame:
            self.current_frame = first_frame

        current_frame = int(self.current_frame)

        center_y, center_x = self.real_position()
        # resize sprite_to_draw
        sprite_to_draw = sprite[:,:,:,current_frame]
        sprite_to_draw = resize_transparent_sprite(sprite_to_draw, height=sprite_height)

        # x, y are exactly the center and the writing is done on topleft corner
        # What if he's too big for the image? well he shouldn't be
        y = int(round(center_y-sprite_to_draw.shape[0]/2))
        x = int(round(center_x-sprite_to_draw.shape[1]/2))
        overlay_transparent(image, sprite_to_draw, y, x)

        if self.show_hp_timer > 0:
            bottom_y = y+sprite_to_draw.shape[0]
            self.draw_hearts(image, y, center_x, bottom_y, sprite_height)

    def draw_hearts(self, image, y, x, bottom_y, sprite_height):
        # If direction == 1, draw it beneath him?
        sprite = self.game.heart_sprite[0]
        threshold = self.max_hp//(self.hearts_shown*2)

        fullheart, halfheart, emptyheart = sprite[:,:,:,0], sprite[:,:,:,1], sprite[:,:,:,2],
        fullheart = resize_transparent_sprite(fullheart, height=sprite_height//3)
        halfheart = resize_transparent_sprite(halfheart, height=sprite_height//3)
        emptyheart = resize_transparent_sprite(emptyheart, height=sprite_height//3)
        left_heart_x = x-(fullheart.shape[1]*self.hearts_shown//2)
        if self.direction == 1 and self.action == 'fighting':
            draw_y = int(round(bottom_y+fullheart.shape[0]/1.5))
        else:
            draw_y = int(round(y-fullheart.shape[0]/1.5))

        for i in range(self.hearts_shown):
            if self.hp <= i * threshold*2:
                sprite_to_draw = emptyheart
            elif self.hp <= i * threshold*2 + threshold:
                sprite_to_draw = halfheart
            else:
                sprite_to_draw = fullheart

            draw_x = left_heart_x+(i*sprite_to_draw.shape[1])
            overlay_transparent(image, sprite_to_draw, draw_y, draw_x)

    def get_sprite(self, direction):
        up, right, down, left = self.sprite
        ordered = [right, up, left, down]

        # Animations:
        if self.action == 'walking':
            sprite = ordered[direction]
            first_frame = 0
            last_frame = 3
        if self.action == 'fighting':
            sprite = ordered[direction]
            first_frame = 3
            last_frame = 7
        if self.action == 'cheering':
            sprite = ordered[direction]
            first_frame = 7
            last_frame = 12
        if self.action == 'dead':
            sprite = ordered[1]
            first_frame = 12
            last_frame = 13

        return sprite, first_frame, last_frame


class Enemy(Mover):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # NOTE: Change for hp/damage
        self.max_hp = 50
        self.hp = self.max_hp
        self.attack_power = 3.5
        # NOTE: Change this for speed
        self.move_speed = 0.5 / self.game.speed_multiplier
        self.image_speed = self.move_speed*2

    def set_patrol(self):
        patrol_cases = [self.spawn]
        for path in self.spawn.paths:
            # Check its not an entrance and not a dog
            if path[0].entrance is False and path[0].value < 5:
                patrol_cases.append(path[0])
        patrol_cases.append(self.spawn)

        # Sets the path of the whole patrol, from spawn to all the paths back to spawn
        self.patrol_path = []
        for prevcase, case in zip(patrol_cases, patrol_cases[1:]):
            path, distance = self.make_path(prevcase, case)
            self.patrol_path += path
        else:
            path, distance = self.make_path(case, self.spawn)
            self.patrol_path += path
        if len(patrol_cases) == 1:
            path, distance = self.make_path(self.spawn, patrol_cases[0])
            self.patrol_path += path
            path, distance = self.make_path(patrol_cases[0], self.spawn)
            self.patrol_path += path

        self.set_path((self.patrol_path, 0))

    def action_walking(self, min_dimension):
        player = self.game.player
        distance = self.real_distance(player)
        if not self.path:
            self.set_path((self.patrol_path, 0))
        if self.action == 'walking':
            if distance <= min_dimension*5:
                if player.moving_to is None:
                    path, distance = self.make_path(self.game.maze.case_array[player.array_y, player.array_x], self.moving_to)
                else:
                    path, distance = self.make_path(player.moving_to, self.moving_to)
                # NOTE edit this for minimum distance to chase the player
                if distance < len(self.game.original_xgrid+self.game.original_ygrid)*1:
                    self.action = 'chasing'

    def action_chasing(self):
        player = self.game.player
        if self.action == 'chasing':
            if self.relative_x == 0 and self.relative_y == 0:
                if player.moving_to is None:
                    path = self.make_path(self.game.maze.case_array[player.array_y, player.array_x], self.moving_to)
                else:
                    path = self.make_path(player.moving_to, self.moving_to)
                self.set_path(path)
                self.path.pop()

    def action_fighting(self):
        player = self.game.player

        if player.fighting[0] == self:
            # change player direction depending on enemy position
            y, x = self.real_position()
            py, px = player.real_position()
            ydelta, xdelta = py-y, px-x
            if abs(ydelta) > abs(xdelta):
                player.direction = 1 if ydelta > 0 else 3
            else:
                player.direction = 2 if xdelta > 0 else 0

        if self.action == 'fighting':
            if player.fighting[0] == self:
                # If player is attacking ME, i get hit
                # print(f'{self} being attacked by player')
                self.change_hp(-player.attack_power)

            if self.action != 'dead':
                player.change_hp(-self.attack_power)
                # print(f'{self} attacked player')
            if self.action == 'dead' or player.action == 'dead':
                # print(player.hp)
                player.remove_fight(self)
                self.remove_fight(player)

    def class_step(self, min_dimension=None):
        min_dimension = min_dimension or 30
        player = self.game.player
        distance = self.real_distance(player)

        if self.action in ['walking', 'chasing']:
            if distance < min_dimension:
                self.action = 'fighting'
                player.action = 'fighting'
                player.add_fight(self)
                self.add_fight(player)

        if self.action == 'walking':
            self.action_walking(min_dimension)
        elif self.action == 'chasing':
            self.action_chasing()
        elif self.action == 'fighting':
            self.action_fighting()

    def draw(self, image, sprite_height):
        sprite = self.sprite[0]
        if self.action == 'dead':
            first_frame = 3
            last_frame = 3
        else:
            first_frame = 0
            last_frame = 3
            self.current_frame += self.image_speed

        if self.current_frame < first_frame or self.current_frame >= last_frame:
            self.current_frame = first_frame
        current_frame = int(self.current_frame)

        y, x = self.real_position()
        # resize sprite_to_draw
        sprite_to_draw = sprite[:,:,:,current_frame]
        sprite_to_draw = resize_transparent_sprite(sprite_to_draw, height=sprite_height)

        # x, y are exactly the center and the writing is done on topleft corner
        # What if he's too big for the image? well he shouldn't be
        y = int(round(y-sprite_to_draw.shape[0]/2))
        x = int(round(x-sprite_to_draw.shape[1]/2))
        overlay_transparent(image, sprite_to_draw, y, x)


class Item(Mover):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.action = 'standing'
        # NOTE: Change for barking time
        self.max_cheer_timer = 30
        self.cheer_timer = self.max_cheer_timer
        # NOTE: Change for doggy speed
        self.move_speed = 0.6 / self.game.speed_multiplier
        self.image_speed = self.move_speed*2

    def class_step(self, min_dimension):
        if self.action == 'walking':
            if self.game.maze.case_array[self.array_y, self.array_x].entrance is True:
                self.game.cheering_dogs.remove(self)

        if self.action == 'cheering':
            self.cheer_timer -= 1
            if self.cheer_timer <= 0:
                self.action = 'walking'

                shortest_path = ([], np.inf)
                for entrance_coords in self.game.maze.entrances:
                    goal = self.game.maze.case_array[entrance_coords]
                    path, distance = self.make_path(goal)
                    # Keep the shortest path to a dougie
                    if distance < shortest_path[1]:
                        shortest_path = (path, distance)
                # If we found is a path, follow it
                if shortest_path[1] != np.inf:
                    self.set_path(shortest_path)
                else:
                    # This should never happen unless you edit with the maze in the middle of it
                    self.game.cheering_dogs.remove(self)
                    print('error exit not found?')
                # find path to nearest exit

    def get_sprite(self, direction):
        left, up, down, right = self.sprite
        ordered = [right, up, left, down]

        # Animations:
        if self.action == 'standing':
            sprite = left
            first_frame = 6
            last_frame = 6
        if self.action == 'walking':
            sprite = ordered[direction]
            first_frame = 0
            last_frame = 3
        if self.action == 'cheering':
            sprite = ordered[direction]
            first_frame = 3
            last_frame = 6

        return sprite, first_frame, last_frame

    def draw(self, image, sprite_height):
        sprite, first_frame, last_frame = self.get_sprite(self.direction)

        self.current_frame += self.image_speed

        if self.current_frame < first_frame or self.current_frame >= last_frame:
            self.current_frame = first_frame

        current_frame = int(self.current_frame)
        # resize sprite_to_draw
        sprite_to_draw = sprite[:,:,:,current_frame]
        sprite_to_draw = resize_transparent_sprite(sprite_to_draw, height=sprite_height)

        # first_y, first_x = self.maze.real_position(self.array_y, self.array_x)
        # y, x = first_y, first_x
        center_y, center_x = self.real_position()
        # x, y are exactly the center and the writing is done on topleft corner
        # What if he's too big for the image? well he shouldn't be
        y = int(round(center_y-sprite_to_draw.shape[0]/2))
        x = int(round(center_x-sprite_to_draw.shape[1]/2))
        overlay_transparent(image, sprite_to_draw, y, x)
