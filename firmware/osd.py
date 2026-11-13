# osd.py, firmware v7
# OSD screen model and backends.
#
# The screen is a grid of text rows. Pages render into that grid. A backend
# sends only the rows that changed since the last frame.
# Backends:
#   NullBackend    : no video output (bench, path not chosen yet)
#   RunCamBackend  : path A, RunCam DisplayPort commands 0x20 to 0x22
#   AT7456 backend : path B, not written until the bench test in
#                    docs/OSD_OPTIONS.md passes
# OSD path is NOT chosen. Probe v2 on hardware decides between A, B and C.
# Plain ASCII only. The Split charset (setting 0) is UNVERIFIED.

PAGE_MAIN = 0
PAGE_INFO = 1
PAGE_MIN = 2
PAGE_COUNT = 3

MENU_ITEMS = ("LASER", "OSD PAGE", "SPLIT MENU", "EXIT")
LASER_MODES = ("off", "continuous", "single")


def fmt_feet(feet):
    if feet is None:
        return "---- FT"
    if feet >= 10000:
        return "%d FT" % int(feet)
    return "%.1f FT" % feet


class Screen:
    def __init__(self, cols, rows):
        self.cols = cols
        self.rows = rows
        self.clear()

    def clear(self):
        self.lines = [[" "] * self.cols for _ in range(self.rows)]

    def put(self, x, y, text):
        if y < 0 or y >= self.rows:
            return
        for i, ch in enumerate(text):
            xx = x + i
            if 0 <= xx < self.cols:
                self.lines[y][xx] = ch

    def put_right(self, y, text):
        self.put(self.cols - len(text), y, text)

    def put_center(self, y, text):
        self.put((self.cols - len(text)) // 2, y, text)

    def row(self, y):
        return "".join(self.lines[y])


class State:
    """Everything the OSD may show. main.py fills it in."""

    def __init__(self):
        self.feet = None
        self.jc02_status = "NOMOD"
        self.laser_mode = "continuous"
        self.marked_feet = None
        self.recording = False
        self.rec_remaining = None   # string from setting 4
        self.sd_capacity = None     # string from setting 3
        self.tv_mode = None         # string from setting 2
        self.cam_time = None        # string from setting 6
        self.link_lq = None
        self.failsafe = True
        self.page = PAGE_MAIN
        self.menu_open = False
        self.menu_index = 0


def render(st, scr):
    scr.clear()
    cx = scr.cols // 2
    cy = scr.rows // 2
    if st.menu_open:
        scr.put_center(1, "MENU")
        for i, item in enumerate(MENU_ITEMS):
            val = ""
            if item == "LASER":
                val = st.laser_mode.upper()
            elif item == "OSD PAGE":
                val = str(st.page + 1)
            mark = ">" if i == st.menu_index else " "
            scr.put(3, 3 + i, "%s %-10s %s" % (mark, item, val))
        return scr
    # Crosshair on every page.
    scr.put(cx, cy, "+")
    if st.page == PAGE_MIN:
        scr.put_center(scr.rows - 2, fmt_feet(st.feet))
        return scr
    rec = "REC" if st.recording else "STBY"
    scr.put(1, 0, rec)
    if st.rec_remaining:
        scr.put_right(0, st.rec_remaining + " ")
    dist = fmt_feet(st.feet)
    if st.jc02_status != "OK":
        dist = dist + " " + st.jc02_status
    scr.put_center(scr.rows - 2, dist)
    if st.marked_feet is not None:
        scr.put_center(scr.rows - 3, "MARK " + fmt_feet(st.marked_feet))
    if st.page == PAGE_INFO:
        if st.sd_capacity:
            scr.put(1, 1, "SD " + st.sd_capacity)
        if st.tv_mode:
            scr.put_right(1, st.tv_mode + " ")
        if st.cam_time:
            scr.put(1, 2, st.cam_time)
        lq = "LQ --" if st.link_lq is None else "LQ %d" % st.link_lq
        if st.failsafe:
            lq = "RC FS"
        scr.put_right(2, lq + " ")
        scr.put(1, scr.rows - 1, "LASER " + st.laser_mode.upper())
    return scr


class NullBackend:
    def __init__(self):
        self.frames = 0

    def show(self, scr):
        self.frames += 1


class RunCamBackend:
    """Path A. Sends changed rows as horizontal strings (0x22).
    Waits for the RunCam queue to drain before the next frame."""

    def __init__(self, cam):
        self.cam = cam
        self.sent = None

    def show(self, scr):
        if not self.cam.disp_ok() or self.cam.busy():
            return
        if self.sent is None or len(self.sent) != scr.rows:
            self.cam.disp_fill(0, 0, scr.cols, scr.rows, 0x20)
            self.sent = [" " * scr.cols for _ in range(scr.rows)]
        for y in range(scr.rows):
            r = scr.row(y)
            if r != self.sent[y]:
                self.cam.disp_string(0, y, r)
                self.sent[y] = r


class OSD:
    def __init__(self, backend, cols, rows):
        self.backend = backend
        self.screen = Screen(cols, rows)
        self.state = State()

    def resize(self, cols, rows):
        self.screen = Screen(cols, rows)

    def update(self):
        render(self.state, self.screen)
        self.backend.show(self.screen)

    def next_page(self):
        self.state.page = (self.state.page + 1) % PAGE_COUNT

    def dump(self):
        return "\n".join(self.screen.row(y) for y in range(self.screen.rows))
