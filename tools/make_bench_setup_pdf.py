# make_bench_setup_pdf.py, bench setup guide v1
# Builds docs/setup/Bench_Setup_RP2040_Split_v1.pdf with reportlab.
# Run from the repo root:  python3 tools/make_bench_setup_pdf.py

import os

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (Flowable, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

VERSION = "v1"
DATE = "2026-11-13"
OUT = os.path.join("docs", "setup", "Bench_Setup_RP2040_Split_%s.pdf" % VERSION)

ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=ss["Heading1"], fontSize=16, spaceAfter=6)
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontSize=12.5, spaceBefore=10, spaceAfter=4)
BODY = ParagraphStyle("B", parent=ss["Normal"], fontSize=9.5, leading=12.5, alignment=TA_LEFT)
NOTE = ParagraphStyle("N", parent=BODY, fontSize=8.5, leading=11, leftIndent=18,
                      textColor=colors.HexColor("#444444"))
STEP = ParagraphStyle("S", parent=BODY, leftIndent=18, firstLineIndent=-14, spaceBefore=2)
WARN = ParagraphStyle("W", parent=BODY, backColor=colors.HexColor("#FFF1D6"),
                      borderColor=colors.HexColor("#D08A00"), borderWidth=0.8, borderPadding=5,
                      spaceBefore=6, spaceAfter=8)
CELL = ParagraphStyle("C", parent=BODY, fontSize=8.5, leading=10.5)

GRID = TableStyle([
    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#999999")),
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E6E6E6")),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
])


def p(t, st=BODY):
    return Paragraph(t, st)


def table(rows, widths, extra=None):
    data = [[p(c, CELL) if isinstance(c, str) else c for c in r] for r in rows]
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(GRID)
    if extra:
        t.setStyle(TableStyle(extra))
    return t


def steps(items, start=1):
    out = []
    n = start
    for it in items:
        if isinstance(it, tuple) and it[0] == "note":
            out.append(p("Note: " + it[1], NOTE))
        else:
            out.append(p("%d.&nbsp;&nbsp;%s" % (n, it), STEP))
            n += 1
    return out


class WiringDiagram(Flowable):
    """Logical wiring diagram. Not to scale, not the physical pad positions."""

    def __init__(self, width=7.0 * inch, height=4.3 * inch):
        super().__init__()
        self.width = width
        self.height = height

    def box(self, c, x, y, w, h, title, sub, fill):
        c.setFillColor(fill)
        c.setStrokeColor(colors.black)
        c.roundRect(x, y, w, h, 6, stroke=1, fill=1)
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(x + w / 2, y + h - 14, title)
        c.setFont("Helvetica", 7.5)
        c.drawCentredString(x + w / 2, y + h - 25, sub)

    def pin(self, c, x, y, label, right):
        c.setFillColor(colors.HexColor("#C9A227"))
        c.rect(x - 4, y - 4, 8, 8, stroke=1, fill=1)
        c.setFillColor(colors.black)
        c.setFont("Helvetica", 8)
        if right:
            c.drawRightString(x - 8, y - 3, label)
        else:
            c.drawString(x + 8, y - 3, label)

    def wire(self, c, x1, y1, x2, y2, color, label, mx, dash=None, width=2):
        c.setStrokeColor(color)
        c.setLineWidth(width)
        if dash:
            c.setDash(*dash)
        path = c.beginPath()
        path.moveTo(x1, y1)
        path.lineTo(mx, y1)
        path.lineTo(mx, y2)
        path.lineTo(x2, y2)
        c.drawPath(path, stroke=1, fill=0)
        c.setDash()
        c.setLineWidth(1)
        c.setFillColor(color)
        c.setFont("Helvetica-Bold", 7.5)
        c.drawString(mx + 5, y2 + 4, label)

    def draw(self):
        c = self.canv
        W, H = self.width, self.height
        # RP2040-Zero
        rx, ry, rw, rh = 0.15 * inch, 0.55 * inch, 2.0 * inch, 3.4 * inch
        self.box(c, rx, ry, rw, rh, "RP2040-Zero", "USB-C to PC (bench power)", colors.HexColor("#DCE8F7"))
        rp = {}
        names = ["GP0  (JC02, keep)", "GP1  (JC02, keep)", "GP2  (JC02, keep)", "GP4  UART1 TX",
                 "GP5  UART1 RX", "GND", "3V3  (JC02 + 470uF, keep)", "5V   (leave open on bench)"]
        for i, n in enumerate(names):
            y = ry + rh - 42 - i * 26
            px = rx + rw
            self.pin(c, px, y, n, right=True)
            rp[n.split()[0]] = (px, y)
        # Split
        sx, sy, sw, sh = W - 2.15 * inch, 1.15 * inch, 2.0 * inch, 2.8 * inch
        self.box(c, sx, sy, sw, sh, "RunCam Split 3 Micro", "orange, SD board", colors.HexColor("#FCE3CF"))
        sp = {}
        for i, n in enumerate(["RX", "TX", "GND", "MENU  (leave open)", "D+  (leave open)", "D-  (leave open)"]):
            y = sy + sh - 45 - i * 30
            sp[n.split()[0]] = (sx, y)
            self.pin(c, sx, y, n, right=False)
        # BEC
        bx, by, bw, bh = W - 2.15 * inch, 0.0 * inch, 2.0 * inch, 0.75 * inch
        self.box(c, bx, by, bw, bh, "5V BEC, 1A or more", "Split power only", colors.HexColor("#E3F2DF"))
        c.setFont("Helvetica", 7.5)
        c.drawString(bx + 8, by + 8, "+5V -> Split 5V in     GND -> Split GND")

        x0 = rx + rw
        self.wire(c, *rp["GP4"], *sp["RX"], colors.HexColor("#1F5FBF"), "W2: GP4 to Split RX",
                  mx=x0 + 0.45 * inch)
        self.wire(c, *rp["GP5"], *sp["TX"], colors.HexColor("#B22222"),
                  "W3: Split TX to GP5 (after step C)", mx=x0 + 0.75 * inch, dash=(4, 3))
        self.wire(c, *rp["GND"], *sp["GND"], colors.black, "W1: GND to GND (first)",
                  mx=x0 + 1.05 * inch)
        c.setFont("Helvetica-Oblique", 7.5)
        c.setFillColor(colors.HexColor("#444444"))
        c.drawString(0.15 * inch, 0.25 * inch,
                     "Logical diagram. Not the physical pad positions. Use the pad map on the next page.")


def build():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    doc = SimpleDocTemplate(OUT, pagesize=letter, leftMargin=0.7 * inch, rightMargin=0.7 * inch,
                            topMargin=0.6 * inch, bottomMargin=0.6 * inch,
                            title="Bench Setup: RP2040-Zero to RunCam Split 3 Micro",
                            author="RuncamMicroSplitv3_CustomPCB")
    s = []
    s.append(p("Bench Setup: RP2040-Zero to RunCam Split 3 Micro", H1))
    s.append(p("Guide %s, %s. Firmware: probe v2, firmware v7 (BENCH_V6 layout). "
               "Last known good on hardware: jc02_debug.py debug v2. "
               "Everything for the Split link is UNVERIFIED on hardware." % (VERSION, DATE)))
    s.append(p("<b>Rule:</b> the JC02 wires (GP0, GP1, GP2, 3V3, GND) and the 470uF cap stay as they are. "
               "This guide adds three wires only: GND, GP4 and GP5.", WARN))

    s.append(p("1. What you need", H2))
    s.append(table([
        ["Item", "Note"],
        ["RP2040-Zero with JC02 already wired", "Current bench board, MicroPython v1.29.0"],
        ["RunCam Split 3 Micro (orange) with SD card", "SD card in the board before power"],
        ["5V BEC, 1A or more", "Split power. Split draws up to 650mA at 5V (manual)."],
        ["Monitor or VTX plus goggles", "To see the analog video and the OSD test"],
        ["Multimeter", "DC volts and continuity"],
        ["Thin wire, solder, flux, heat shrink", "Short wires. Keep them under 6 in if you can."],
        ["Resistor kit (1/4W)", "Only if the Split TX measures above 3.3V (step C)"],
        ["PC with mpremote", "<font face='Courier'>pip install mpremote</font>"],
    ], [2.6 * inch, 4.4 * inch]))

    s.append(p("2. Wiring overview", H2))
    s.append(WiringDiagram())
    s.append(Spacer(1, 6))
    s.append(table([
        ["Wire", "From (RP2040-Zero)", "To (Split)", "When"],
        ["W1", "GND pad", "GND pad", "First. Step D1."],
        ["W2", "GP4 (UART1 TX)", "RX pad", "Step D2."],
        ["W3", "GP5 (UART1 RX)", "TX pad", "Only after step C passes."],
        ["none", "5V pad", "none", "Leave open on the bench. RP2040 runs from USB."],
        ["none", "spare GPIO", "MENU pad", "Leave open. Active level UNVERIFIED."],
        ["none", "none", "D+, D-", "Leave open. USB only."],
    ], [0.6 * inch, 1.9 * inch, 1.5 * inch, 3.0 * inch]))
    s.append(p("Note: TX goes to RX, RX goes to TX. A straight TX-to-TX wire gives no reply.", NOTE))

    s.append(p("3. RP2040-Zero pad map", H2))
    s.append(p("View: chip side up, USB-C at the top. GPIO edge on the left, power edge on the right. "
               "This orientation was read from the 2026-11-13 photos and the JC02 wire colors, not from the "
               "silkscreen. <b>Check the silkscreen before you solder.</b> Pads used in this guide are shaded."))
    hl = colors.HexColor("#FFE9A8")
    keep = colors.HexColor("#E0E0E0")
    pad_rows = [["GPIO edge (left), top to bottom", "Power edge (right), top to bottom", "Bottom edge"],
                ["GP0  JC02 black (keep)", "5V  (open on bench)", "GP13"],
                ["GP1  JC02 yellow (keep)", "GND  JC02 white + cap (keep) + W1", "GP12"],
                ["GP2  JC02 red (keep)", "3V3  JC02 blue + cap (keep)", "GP11"],
                ["GP3", "GP29", "GP10"],
                ["GP4  W2 to Split RX", "GP28", "GP9"],
                ["GP5  W3 from Split TX", "GP27", ""],
                ["GP6", "GP26", ""],
                ["GP7", "GP15", ""],
                ["GP8  (position UNVERIFIED)", "GP14  (position UNVERIFIED)", ""]]
    s.append(table(pad_rows, [2.5 * inch, 2.7 * inch, 1.8 * inch], [
        ("BACKGROUND", (0, 1), (0, 3), keep), ("BACKGROUND", (1, 2), (1, 3), keep),
        ("BACKGROUND", (0, 5), (0, 6), hl), ("BACKGROUND", (1, 2), (1, 2), hl),
    ]))
    s.append(p("Note: W1 can go on any GND pad. The GND pad already has the JC02 white wire and a cap lead. "
               "If it is crowded, use a GND point on the back of the board or on the Split side of the BEC.", NOTE))

    s.append(p("A. Back up the board", H2))
    s += steps([
        "Connect the RP2040-Zero to the PC with USB-C.",
        "Copy the current main.py from the board to the PC:<br/>"
        "<font face='Courier'>mkdir -p board_backup &amp;&amp; mpremote cp :main.py board_backup/main.py</font>",
        "List the board files and keep the list: <font face='Courier'>mpremote ls</font>",
        "Disconnect USB.",
        ("note", "This backup is your rollback if anything goes wrong later."),
    ])

    s.append(p("B. Test the Split alone", H2))
    s += steps([
        "Put the SD card in the Split.",
        "Connect the Split video out to the monitor or VTX.",
        "Connect the BEC +5V and GND to the Split power pads. Do not connect the RP2040 yet.",
        "Apply power. Wait 10 seconds.",
        "Make sure you see the camera image.",
        "Press the Split button to record for 10 seconds, then stop. Make sure the file is on the SD card.",
        ("note", "This proves the Split works before you add anything to it."),
    ])

    s.append(p("C. Measure the Split pads (do not skip)", H2))
    s += steps([
        "Keep the Split powered from the BEC. Keep the RP2040 disconnected.",
        "Set the meter to DC volts.",
        "Put the black probe on Split GND.",
        "Put the red probe on the Split TX pad. Write the value in the record sheet.",
        "Put the red probe on the Split MENU pad. Write the value in the record sheet.",
        "Remove power.",
    ])
    s.append(table([
        ["Split TX reads", "Action"],
        ["3.3V or less", "Pass. Solder W3 direct to GP5 in step D."],
        ["Above 3.3V (for example near 5V)", "Do not connect TX to GP5 directly. Add a divider: Split TX to a 2.2k "
         "resistor to GP5, and GP5 to a 3.3k resistor to GND. At 5V in this gives about 3.0V at GP5. "
         "Measure GP5 side again before you connect the RP2040."],
        ["0V", "TX may be idle-low or not active yet. Wait 10 s after power and measure again. "
               "If still 0V, stop and report it."],
    ], [2.2 * inch, 4.8 * inch]))
    s.append(p("Note: RP2040 pins are 3.3V only. 5V on GP5 can damage the RP2040.", NOTE))

    s.append(p("D. Solder the link", H2))
    s += steps([
        "Remove all power. Unplug USB and the BEC.",
        "Solder W1: RP2040-Zero GND to Split GND.",
        "Solder W2: RP2040-Zero GP4 to Split RX.",
        "If step C passed, solder W3: Split TX to RP2040-Zero GP5 (through the divider if step C needs it).",
        "Do not connect MENU, D+, D- or the RP2040 5V pad.",
        "Insulate each joint with heat shrink or tape.",
    ])

    s.append(p("E. Check before power", H2))
    s += steps([
        "Set the meter to continuity.",
        "Check GP4 to Split RX: beep.",
        "Check GP5 to Split TX: beep (or the divider resistance if fitted).",
        "Check RP2040 GND to Split GND: beep.",
        "Check GP4 to GP5: no beep.",
        "Check GP4 to GND and GP5 to GND: no beep.",
        "Check Split 5V to GND: no beep.",
        "Check RP2040 3V3 to GND: no dead short. The 470uF cap can beep for a moment while it charges. That is normal.",
    ])

    s.append(p("F. Power up order", H2))
    s += steps([
        "Connect the BEC to the Split. Apply BEC power.",
        "Wait for the camera image on the monitor.",
        "Connect the RP2040-Zero to the PC with USB-C.",
        ("note", "On the bench the RP2040 runs from USB only. Do not connect the BEC 5V to the RP2040 5V pad while "
                 "USB is connected. It can back-feed the PC port. Whether the module has a diode on USB power is "
                 "UNVERIFIED."),
        "Power down in the reverse order: USB first, then the BEC.",
    ])

    s.append(p("G. Run probe v2", H2))
    s += steps([
        "On the PC, open tools/runcam_probe_v2.py.",
        "Set <font face='Courier'>SPLIT_TX_MEASURED_OK = True</font> only if step C passed.",
        "Leave <font face='Courier'>OSD_WRITE_TEST = False</font> for the first run.",
        "Run it from the repo root: <font face='Courier'>mpremote run tools/runcam_probe_v2.py</font>",
        "Wait about 20 seconds. The probe waits 8 seconds for the Split to boot.",
        "Copy all output from \"runcam probe v2\" to \"done\" and paste it in the chat.",
        "For the second run, set <font face='Courier'>OSD_WRITE_TEST = True</font>. Start a recording on the Split "
        "with its own button first, then run the probe.",
        "Look for \"PROBE V2 OSD\" near the top left of the live image for 10 seconds.",
        "Stop the recording. Check the SD file for the same text.",
        ("note", "The probe never starts or stops recording and never changes camera settings. "
                 "It only reads, plus the OSD text test when you turn it on."),
    ])

    s.append(p("H. Troubleshooting", H2))
    s.append(table([
        ["Symptom in the probe log", "Check"],
        ["\"STOP. Measure Split TX\"", "Flag not set. Do step C, then set SPLIT_TX_MEASURED_OK = True."],
        ["RX (none) on every try", "W2/W3 swapped. Common GND missing. Split not powered. Split not fully booted."],
        ["RX shows random bytes", "GND missing or poor. Baud mismatch. Wire too long or near the VTX antenna."],
        ["Legacy RCSplit detect: REPLIED", "Old protocol. Report the log. Firmware v7 does not support it yet."],
        ["Device info OK, OSD test skipped", "Split does not report DisplayPort (bit 5). OSD path A is out."],
        ["Board resets when the Split powers up", "Ground loop or supply dip. Check that the BEC GND and the USB GND "
                                                  "meet only at W1. Report it."],
    ], [2.4 * inch, 4.6 * inch]))

    s.append(p("I. Optional: flash firmware v7", H2))
    s.append(p("<b>This overwrites main.py on the board.</b> Do step A first. Rollback: "
               "<font face='Courier'>mpremote cp board_backup/main.py :main.py</font> then "
               "<font face='Courier'>mpremote reset</font>.", WARN))
    s += steps([
        "Go to the firmware folder: <font face='Courier'>cd firmware</font>",
        "Copy the files: <font face='Courier'>mpremote cp config.py crc.py jc02.py runcam.py crsf.py osd.py "
        "pio_uart.py status_led.py main.py :</font>",
        "Reset: <font face='Courier'>mpremote reset</font>",
        "Watch the output: <font face='Courier'>mpremote repl</font>",
        "Make sure $JC02 lines show and the LED goes green on a good reading.",
        "After 7 seconds, look for a line that starts with \"# runcam ready\".",
        ("note", "LAYOUT stays BENCH_V6. The JC02 stays on GP0, GP1, GP2. CRSF is off in this layout."),
    ])

    s.append(p("J. Record sheet", H2))
    s.append(table([
        ["Item", "Value"],
        ["Date", ""],
        ["Split TX idle voltage (step C)", ""],
        ["Split MENU idle voltage (step C)", ""],
        ["Divider fitted on GP5 (yes/no, values)", ""],
        ["Probe: protocol version", ""],
        ["Probe: features (hex)", ""],
        ["Probe: settings read OK (yes/no)", ""],
        ["OSD text on live feed (yes/no)", ""],
        ["OSD text in SD recording (yes/no)", ""],
        ["Firmware v7 flashed (yes/no), result", ""],
        ["Notes", "<br/><br/><br/>"],
    ], [3.0 * inch, 4.0 * inch], [("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F6F6F6")])]))
    s.append(Spacer(1, 8))
    s.append(p("Changelog guide v1: first issue. Covers RP2040-Zero to Split UART link, measurement, probe v2, "
               "optional firmware v7. Untested on hardware.", NOTE))

    def footer(canvas, d):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor("#666666"))
        canvas.drawString(0.7 * inch, 0.35 * inch, "Bench setup guide %s, %s" % (VERSION, DATE))
        canvas.drawRightString(letter[0] - 0.7 * inch, 0.35 * inch, "Page %d" % d.page)
        canvas.restoreState()

    doc.build(s, onFirstPage=footer, onLaterPages=footer)
    print(OUT)


if __name__ == "__main__":
    build()
