import math
import matplotlib.pyplot as plt
import random
import numpy as np

show_animation = True
pause_time = 0.001
p_create_random_obstacle = 0.2 # Increased probability for random obstacles


class Node:
    def __init__(self, x: int = 0, y: int = 0, cost: float = 0.0):
        self.x = x
        self.y = y
        self.cost = cost


def add_coordinates(node1: Node, node2: Node):
    new_node = Node()
    new_node.x = node1.x + node2.x
    new_node.y = node1.y + node2.y
    new_node.cost = node1.cost + node2.cost
    return new_node


def compare_coordinates(node1: Node, node2: Node):
    return node1.x == node2.x and node1.y == node2.y


class DStarLite:

    # Please adjust the heuristic function (h) if you change the list of
    # possible motions
    motions = [
        Node(1, 0, 1),
        Node(0, 1, 1),
        Node(-1, 0, 1),
        Node(0, -1, 1),
        Node(1, 1, math.sqrt(2)),
        Node(1, -1, math.sqrt(2)),
        Node(-1, 1, math.sqrt(2)),
        Node(-1, -1, math.sqrt(2))
    ]

    def __init__(self, ox: list, oy: list):
        # Ensure that within the algorithm implementation all node coordinates
        # are indices in the grid and extend
        # from 0 to abs(<axis>_max - <axis>_min)
        self.x_min_world = int(min(ox))
        self.y_min_world = int(min(oy))
        self.x_max = int(abs(max(ox) - self.x_min_world))
        self.y_max = int(abs(max(oy) - self.y_min_world))
        self.obstacles = [Node(x - self.x_min_world, y - self.y_min_world)
                          for x, y in zip(ox, oy)]
        self.obstacles_xy = {(obstacle.x, obstacle.y) for obstacle in self.obstacles}
        self.start = Node(0, 0)
        self.goal = Node(0, 0)
        self.U = list()
        self.km = 0.0
        self.kold = 0.0
        self.rhs = self.create_grid(float("inf"))
        self.g = self.create_grid(float("inf"))
        self.detected_obstacles_xy: set[tuple[int, int]] = set()
        self.xy = np.empty((0, 2))
        if show_animation:
            self.detected_obstacles_for_plotting_x = list()
            self.detected_obstacles_for_plotting_y = list()
        self.initialized = False

    def create_grid(self, val: float):
        return np.full((self.x_max, self.y_max), val)

    def is_obstacle(self, node: Node):
        is_in_obstacles = (node.x, node.y) in self.obstacles_xy
        is_in_detected_obstacles = (node.x, node.y) in self.detected_obstacles_xy
        return is_in_obstacles or is_in_detected_obstacles

    def c(self, node1: Node, node2: Node):
        if self.is_obstacle(node2):
            # Attempting to move from or to an obstacle
            return math.inf
        new_node = Node(node1.x-node2.x, node1.y-node2.y)
        detected_motion = list(filter(lambda motion:
                                       compare_coordinates(motion, new_node),
                                       self.motions))
        return detected_motion[0].cost

    def h(self, s: Node):
        # Cannot use the 2nd euclidean norm as this might sometimes generate
        # heuristics that overestimate the cost, making them inadmissible,
        # due to rounding errors etc (when combined with calculate_key)
        # To be admissible heuristic should
        # never overestimate the cost of a move
        # hence not using the line below
        # return math.hypot(self.start.x - s.x, self.start.y - s.y)

        # Below is the same as 1; modify if you modify the cost of each move in
        # motion
        # return max(abs(self.start.x - s.x), abs(self.start.y - s.y))
        return 1

    def calculate_key(self, s: Node):
        return (min(self.g[s.x][s.y], self.rhs[s.x][s.y]) + self.h(s)
                + self.km, min(self.g[s.x][s.y], self.rhs[s.x][s.y]))

    def is_valid(self, node: Node):
        if 0 <= node.x < self.x_max and 0 <= node.y < self.y_max:
            return True
        return False

    def get_neighbours(self, u: Node):
        return [add_coordinates(u, motion) for motion in self.motions
                if self.is_valid(add_coordinates(u, motion))]

    def pred(self, u: Node):
        # Grid, so each vertex is connected to the ones around it
        return self.get_neighbours(u)

    def succ(self, u: Node):
        # Grid, so each vertex is connected to the ones around it
        return self.get_neighbours(u)

    def initialize(self, start: Node, goal: Node):
        self.start.x = start.x - self.x_min_world
        self.start.y = start.y - self.y_min_world
        self.goal.x = goal.x - self.x_min_world
        self.goal.y = goal.y - self.y_min_world
        if not self.initialized:
            self.initialized = True
            print('Initializing')
            self.U = list()
            self.km = 0.0
            self.rhs = self.create_grid(math.inf)
            self.g = self.create_grid(math.inf)
            self.rhs[self.goal.x][self.goal.y] = 0
            self.U.append((self.goal, self.calculate_key(self.goal)))
            self.detected_obstacles_xy = set()

    def update_vertex(self, u: Node):
        if not compare_coordinates(u, self.goal):
            self.rhs[u.x][u.y] = min([self.c(u, sprime) +
                                     self.g[sprime.x][sprime.y]
                                     for sprime in self.succ(u)])
        if any([compare_coordinates(u, node) for node, key in self.U]):
            self.U = [(node, key) for node, key in self.U
                      if not compare_coordinates(node, u)]
            self.U.sort(key=lambda x: x[1])
        if self.g[u.x][u.y] != self.rhs[u.x][u.y]:
            self.U.append((u, self.calculate_key(u)))
            self.U.sort(key=lambda x: x[1])

    def compare_keys(self, key_pair1: tuple[float, float],
                     key_pair2: tuple[float, float]):
        return key_pair1[0] < key_pair2[0] or \
               (key_pair1[0] == key_pair2[0] and key_pair1[1] < key_pair2[1])

    def compute_shortest_path(self):
        self.U.sort(key=lambda x: x[1])
        has_elements = len(self.U) > 0
        # The original code had an issue with `(self.g[u.x, u.y] > self.rhs[u.x, u.y]).any()` which is not needed here
        # since u.x and u.y will be single values, hence fixed this.
        while has_elements and self.compare_keys(self.U[0][1], self.calculate_key(self.start)) or \
                self.rhs[self.start.x][self.start.y] != self.g[self.start.x][self.start.y]:
            self.kold = self.U[0][1]
            u = self.U[0][0]
            self.U.pop(0)
            if self.compare_keys(self.kold, self.calculate_key(u)):
                self.U.append((u, self.calculate_key(u)))
                self.U.sort(key=lambda x: x[1])
            elif self.g[u.x][u.y] > self.rhs[u.x][u.y]:
                self.g[u.x][u.y] = self.rhs[u.x][u.y]
                for s in self.pred(u):
                    self.update_vertex(s)
            else:
                self.g[u.x][u.y] = math.inf
                for s in self.pred(u) + [u]:
                    self.update_vertex(s)
            self.U.sort(key=lambda x: x[1])
            has_elements = len(self.U) > 0


    def detect_changes(self):
        changed_vertices = list()
        if len(self.spoofed_obstacles) > 0:
            for spoofed_obstacle in self.spoofed_obstacles[0]:
                if compare_coordinates(spoofed_obstacle, self.start) or \
                   compare_coordinates(spoofed_obstacle, self.goal):
                    continue
                changed_vertices.append(spoofed_obstacle)
                self.detected_obstacles_xy.add((spoofed_obstacle.x, spoofed_obstacle.y))
                if show_animation:
                    self.detected_obstacles_for_plotting_x.append(
                        spoofed_obstacle.x + self.x_min_world)
                    self.detected_obstacles_for_plotting_y.append(
                        spoofed_obstacle.y + self.y_min_world)
                    plt.plot(self.detected_obstacles_for_plotting_x,
                             self.detected_obstacles_for_plotting_y, ".k")
                    plt.pause(pause_time)
            self.spoofed_obstacles.pop(0)

        # Allows random generation of obstacles
        random.seed()
        if random.random() < p_create_random_obstacle: # Changed from > 1 - p_create_random_obstacle
            x = random.randint(0, self.x_max - 1)
            y = random.randint(0, self.y_max - 1)
            new_obs = Node(x, y)
            if compare_coordinates(new_obs, self.start) or \
               compare_coordinates(new_obs, self.goal):
                return changed_vertices
            # Ensure the random obstacle isn't already a static obstacle
            if (x, y) not in self.obstacles_xy and (x, y) not in self.detected_obstacles_xy:
                changed_vertices.append(Node(x, y))
                self.detected_obstacles_xy.add((x, y))
                if show_animation:
                    self.detected_obstacles_for_plotting_x.append(x +
                                                                   self.x_min_world)
                    self.detected_obstacles_for_plotting_y.append(y +
                                                                   self.y_min_world)
                    plt.plot(self.detected_obstacles_for_plotting_x,
                             self.detected_obstacles_for_plotting_y, ".k")
                    plt.pause(pause_time)
        return changed_vertices

    def compute_current_path(self):
        path = list()
        current_point = Node(self.start.x, self.start.y)
        while not compare_coordinates(current_point, self.goal):
            path.append(current_point)
            # Find the successor with the minimum cost
            successors = self.succ(current_point)
            if not successors:  # No successors, path blocked
                return []
            
            min_cost_sprime = None
            min_total_cost = math.inf
            
            for sprime in successors:
                cost = self.c(current_point, sprime) + self.g[sprime.x][sprime.y]
                if cost < min_total_cost:
                    min_total_cost = cost
                    min_cost_sprime = sprime
            
            if min_cost_sprime is None or min_total_cost == math.inf:
                # If no valid path to a successor, or all are infinite cost
                return [] # Indicates a blocked path

            current_point = min_cost_sprime

        path.append(self.goal)
        return path

    def compare_paths(self, path1: list, path2: list):
        if len(path1) != len(path2):
            return False
        for node1, node2 in zip(path1, path2):
            if not compare_coordinates(node1, node2):
                return False
        return True

    def display_path(self, path: list, colour: str, alpha: float = 1.0):
        px = [(node.x + self.x_min_world) for node in path]
        py = [(node.y + self.y_min_world) for node in path]
        drawing = plt.plot(px, py, colour, alpha=alpha)
        plt.pause(pause_time)
        return drawing

    def main(self, start: Node, goal: Node,
             spoofed_ox: list, spoofed_oy: list):
        self.spoofed_obstacles = [[Node(x - self.x_min_world,
                                        y - self.y_min_world)
                                   for x, y in zip(rowx, rowy)]
                                   for rowx, rowy in zip(spoofed_ox, spoofed_oy)
                                  ]
        pathx = []
        pathy = []
        self.initialize(start, goal)
        last = self.start
        self.compute_shortest_path()
        pathx.append(self.start.x + self.x_min_world)
        pathy.append(self.start.y + self.y_min_world)

        if show_animation:
            current_path = self.compute_current_path()
            if not current_path: # Handle initial blocked path
                print("No initial path possible")
                return False, pathx, pathy

            previous_path = current_path.copy()
            previous_path_image = self.display_path(previous_path, ".c",
                                                    alpha=0.3)
            current_path_image = self.display_path(current_path, ".c")

        while not compare_coordinates(self.goal, self.start):
            if self.g[self.start.x][self.start.y] == math.inf:
                print("No path possible")
                return False, pathx, pathy
            
            # Move to the next node on the current path
            successors = self.succ(self.start)
            if not successors: # Agent is stuck
                print("Agent is stuck, no valid successors.")
                return False, pathx, pathy

            next_node = None
            min_cost = math.inf
            for sprime in successors:
                cost = self.c(self.start, sprime) + self.g[sprime.x][sprime.y]
                if cost < min_cost:
                    min_cost = cost
                    next_node = sprime
            
            if next_node is None: # Should ideally not happen if g-values are correct
                print("Could not determine next step on path.")
                return False, pathx, pathy

            self.start = next_node
            
            pathx.append(self.start.x + self.x_min_world)
            pathy.append(self.start.y + self.y_min_world)
            if show_animation:
                # Only pop if current_path is not empty and we successfully moved
                if current_path:
                    current_path.pop(0) 
                plt.plot(pathx, pathy, "-r")
                plt.pause(pause_time)
            
            changed_vertices = self.detect_changes()
            if len(changed_vertices) != 0:
                print("New obstacle detected")
                self.km += self.h(last)
                last = self.start
                for u in changed_vertices:
                    if compare_coordinates(u, self.start):
                        continue
                    self.rhs[u.x][u.y] = math.inf
                    self.g[u.x][u.y] = math.inf
                    self.update_vertex(u)
                self.compute_shortest_path()

                if show_animation:
                    new_path = self.compute_current_path()
                    if new_path: # Only update if a new path is found
                        if not self.compare_paths(current_path, new_path):
                            current_path_image[0].remove()
                            previous_path_image[0].remove()
                            previous_path = current_path.copy()
                            current_path = new_path.copy()
                            previous_path_image = self.display_path(previous_path,
                                                                    ".c",
                                                                    alpha=0.3)
                            current_path_image = self.display_path(current_path,
                                                                    ".c")
                            plt.pause(pause_time)
                    else:
                        print("Path blocked after new obstacle detection, no new path found.")
                        # Clear existing path drawings if no new path can be found
                        if current_path_image:
                            current_path_image[0].remove()
                        if previous_path_image:
                            previous_path_image[0].remove()


        print("Path found")
        return True, pathx, pathy


def main():

    # start and goal position
    sx = 10  # [m]
    sy = 10  # [m]
    gx = 50  # [m]
    gy = 50  # [m]

    # set obstacle positions
    ox, oy = [], []
    for i in range(-10, 60):
        ox.append(i)
        oy.append(-10.0)
    for i in range(-10, 60):
        ox.append(60.0)
        oy.append(i)
    for i in range(-10, 61):
        ox.append(i)
        oy.append(60.0)
    for i in range(-10, 61):
        ox.append(-10.0)
        oy.append(i)
    for i in range(-10, 40):
        ox.append(20.0)
        oy.append(i)
    for i in range(0, 40):
        ox.append(40.0)
        oy.append(60.0 - i)

    if show_animation:
        plt.plot(ox, oy, ".k")
        plt.plot(sx, sy, "og")
        plt.plot(gx, gy, "xb")
        plt.grid(True)
        plt.axis("equal")
        label_column = ['Start', 'Goal', 'Path taken',
                        'Current computed path', 'Previous computed path',
                        'Obstacles']
        columns = [plt.plot([], [], symbol, color=colour, alpha=alpha)[0]
                   for symbol, colour, alpha in [['o', 'g', 1],
                                                  ['x', 'b', 1],
                                                  ['-', 'r', 1],
                                                  ['.', 'c', 1],
                                                  ['.', 'c', 0.3],
                                                  ['.', 'k', 1]]]
        plt.legend(columns, label_column, bbox_to_anchor=(1, 1), title="Key:",
                   fontsize="xx-small")
        plt.plot()
        plt.show(block=False) # Changed to non-blocking show to allow animation updates


    # Removed or commented out spoofed_ox and spoofed_oy to allow random obstacles
    spoofed_ox = [[]] # Keep empty lists to maintain the structure of the function call
    spoofed_oy = [[]]

    dstarlite = DStarLite(ox, oy)
    path_found, final_pathx, final_pathy = dstarlite.main(Node(x=sx, y=sy), Node(x=gx, y=gy),
                     spoofed_ox=spoofed_ox, spoofed_oy=spoofed_oy)

    if show_animation and path_found:
        plt.plot(final_pathx, final_pathy, "-r") # Plot the final path
        plt.show() # Keep the plot open at the end

if __name__ == "__main__":
    main()