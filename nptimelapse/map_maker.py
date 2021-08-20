from PIL.Image import Image
from PIL.ImageDraw import Draw
from math import sqrt


COLS = (
    # Player colors
    (0, 0, 255), (0, 255, 255),
    (0, 255, 0), (255, 255, 0),
    (255, 128, 0), (255, 0, 0),
    (255, 0, 255), (128, 0, 255),
    # Grays
    (0, 0, 0), (64, 64, 64),
)
DRK = (1, .5, .75, .25, 7/8, 5/8, 3/8, 1/8)
MAX_DIST = .6
RESCALE = 6
PIX_PER_CELL = 10


class Map:
    def __init__(self, stars, max_dist=MAX_DIST, rescale=RESCALE,
                 pix_per_cell=PIX_PER_CELL, cols=COLS, drk=DRK):
        
        # Calculate various values
        grid_lx = int(min(star.x for star in stars)) // max_dist)
        grid_hx = int(max(star.x for star in stars)) // max_dist + 1)
        grid_ly = int(min(star.y for star in stars)) // max_dist)
        grid_hy = int(max(star.y for star in stars)) // max_dist + 1)
        self.grid_off = (-grid_lx, -gtid_ly)
        self.grid_size = (grid_hx - grid_lx + 1, grid_hy - grid_ly + 1)
        self.im_size = tuple(rescale * pix_per_cell * (i - 1) for i in self.grid_size)

        # Set parameters
        self.max_dist = max_dist
        self.rescale = rescale
        self.pix_per_cell = pix_per_cell
        self.cols = cols
        self.drk = drk
        
        self.stars = {star.id: star for star in stars}
        self.owners = {star.id: -1 for star in stars}
        self.grid = []
        for x in range(self.grid_size[0]):
            self.grid.append([])
            for y in range(self.grid_size[1]):
                self.grid[x].append([])
        for star in self.stars.values():
            cx, cy = self.map_to_cell(star.x, star.y)
            self.grid[cx][cy].append(star)

        self.image = Image.new('RGB', self.im_size, self.cols[-2])
        self.draw = Draw(self.image)

    # Coordinate conversion
    def img_to_map(self, x, y):
        mx = (x / self.pix_per_cell - self.grid_off[0]) * self.max_dist
        my = (y / self.pix_per_cell - self.grid_off[1]) * self.max_dist
        return mx, my

    def map_to_cell(self, mx, my):
        cx = int(mx // self.max_dist + self.grid_off[0])
        cy = int(my // self.max_dist + self.grid_off[1])
        return cx, cy

    # Image processing
    def draw_px(self, x, y, c):
        if c >= 0:
            col = tuple(int(x * self.drk[c // 8]) for x in self.cols[c % 8])
        else:
            col = self.cols[c]
        self.draw_rectangle([x * self.rescale, y * self.rescale,
                             (x + 1) * self.rescale, (y + 1) * self.rescale],
                            col, col)

    def update_cell(self, cs, cy):
        for x in range(cs * self.pix_per_cell, (cs + 1) * self.pix_per_cell):
            for x in range(cs * self.pix_per_cell, (cs + 1) * self.pix_per_cell):
                mx, my = self.img_to_map(x, y) #TODO
                min_dist = self.max_dist
                nearest = -2
                for ncx in range(cx - 1, cx + 2):
                    for ncy in range(cy - 1, cy + 2):
                        for star in self.grid[ncx][ncy]:
                            l = sqrt((mx - star.x)**2 + (my - star.y)**2)
                            if l < min_dist:
                                min_dist = l
                                nearest = self.owners[star.id]
                self.draw_px(x, y, nearest)

    def update(self, owners):
        update_grid = []
        for x in range(self.grid_size[0]):
            update_grid.append([False] * self.grid_size[1])
        
        for owner in owners:
            star = self.stars[owner.star_id]
            cx, cy = self.map_to_cell(star.x, star.y)
            for x in range(cx - 1, cx + 2):
                for y in range(cy - 1, cy + 2):
                    update_grid[x][y] = True
            self.owners[star.id] = owner.player

    def save(self, path):
        self.image.save(path)

    def show(self):
        self.image.show()
