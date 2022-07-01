import PIL.Image
from PIL.ImageDraw import Draw
from math import sqrt


BASE = (
    # Player colors
    (0, 0, 255), (0, 255, 255),
    (0, 255, 0), (255, 255, 0),
    (255, 128, 0), (255, 0, 0),
    (255, 0, 255), (128, 0, 255),
)
GREY = ((255, 255, 255), (0, 0, 0), (64, 64, 64))
DRK = (1, .5, .75, .25, 7/8, 5/8, 3/8, 1/8)
COLS = tuple(tuple(int(v * d) for v in c) for d in DRK for c in BASE) + GREY

MAX_DIST = .6
RESCALE = 6
PIX_PER_CELL = 10
BORDER = -1
'''
PPC = 60 / RESCALE
BOR = RESCALE / 100
'''


class Map:
    def __init__(self, stars, max_dist=MAX_DIST, rescale=RESCALE, border=BORDER,
                 pix_per_cell=PIX_PER_CELL, cols=COLS, star_cols=COLS):
        
        # Calculate various values
        # Max and min x and y values
        grid_lx = int(min(star.x for star in stars) // max_dist)
        grid_hx = int(max(star.x for star in stars) // max_dist) + 1
        grid_ly = int(min(star.y for star in stars) // max_dist)
        grid_hy = int(max(star.y for star in stars) // max_dist) + 1
        self.grid_off = (-grid_lx, -grid_ly)  # Grid offset
        self.grid_size = (grid_hx - grid_lx + 1, grid_hy - grid_ly + 1)
        self.im_size = tuple(rescale * pix_per_cell * (i - 1) for i in self.grid_size)

        # Set parameters
        self.max_dist = max_dist
        self.rescale = rescale  # How many actual pixels per percieved pixel
        self.pix_per_cell = pix_per_cell  # How many percieved pixels per grid cell
        self.cols = tuple(tuple(t) for t in cols)  # Colors
        self.star_cols = tuple(tuple(t) for t in star_cols)  # Star colors
        self.border = border  # Border "width"

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

        self.image = PIL.Image.new('RGB', self.im_size, self.cols[-2])
        self.draw = Draw(self.image)
        for x in range(self.grid_size[0] - 1):
            for y in range(self.grid_size[1] - 1):
                self.update_cell(x, y)
        self.draw_stars()

    # Coordinate conversion
    # Percieved pixels to np coordinates
    def img_to_map(self, x, y):
        mx = (x / self.pix_per_cell - self.grid_off[0]) * self.max_dist
        my = (y / self.pix_per_cell - self.grid_off[1]) * self.max_dist
        return mx, my

    # Np coordinates to grid cells
    def map_to_cell(self, mx, my):
        cx = int(mx // self.max_dist) + self.grid_off[0]
        cy = int(my // self.max_dist) + self.grid_off[1]
        return cx, cy

    # Np coordinates to percieved pixels
    def map_to_img(self, mx, my):
        x = int((mx / self.max_dist + self.grid_off[0]) * self.pix_per_cell)
        y = int((my / self.max_dist + self.grid_off[1]) * self.pix_per_cell)
        return x, y

    # Image processing
    # Draw a percieved pixel
    def draw_px(self, x, y, c):
        self.draw.rectangle([x * self.rescale, y * self.rescale,
                             (x + 1) * self.rescale - 1, (y + 1) * self.rescale - 1],
                            c, c)

    # Draw percieved pixels for stars
    def draw_stars(self):
        for star in self.stars.values():
            x, y = self.map_to_img(star.x, star.y)
            self.draw_px(x, y, self.star_cols[self.owners[star.id]])

    # Redraw a grid cell
    def update_cell(self, cx, cy):
        for x in range(cx * self.pix_per_cell, (cx + 1) * self.pix_per_cell):
            for y in range(cy * self.pix_per_cell, (cy + 1) * self.pix_per_cell):
                mx, my = self.img_to_map(x, y)
                min_dist = self.max_dist
                nearest = -2
                for ncx in range(cx - 1, cx + 2):
                    for ncy in range(cy - 1, cy + 2):
                        for star in self.grid[ncx][ncy]:
                            l = sqrt((mx - star.x)**2 + (my - star.y)**2)
                            if abs(min_dist - l) <= self.border:
                                nearest = -2
                            if l < min_dist:
                                if abs(min_dist - l) > self.border:
                                    nearest = self.owners[star.id]
                                min_dist = l
                self.draw_px(x, y, self.cols[nearest])

    def update(self, owners):
        update_grid = []
        for x in range(self.grid_size[0]):
            update_grid.append([False] * self.grid_size[1])
        
        for owner in owners:
            star = self.stars[owner.star_id]
            if self.owners[star.id] != owner.player:
                cx, cy = self.map_to_cell(star.x, star.y)
                # Mark each possibly affected grid cell
                for x in range(cx - 1, cx + 2):
                    for y in range(cy - 1, cy + 2):
                        update_grid[x][y] = True
                self.owners[star.id] = owner.player

        # Redraw every possibly affected cell
        for x in range(self.grid_size[0] - 1):
            for y in range(self.grid_size[1] - 1):
                if update_grid[x][y]:
                    self.update_cell(x, y)

        self.draw_stars()

    def save(self, path):
        self.image.save(path)

    def show(self):
        self.image.show()
