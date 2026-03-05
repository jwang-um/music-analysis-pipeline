"""Google Material-inspired color scheme and QSS stylesheet."""

PRIMARY = '#1A73E8'
PRIMARY_HOVER = '#1765CC'
PRIMARY_LIGHT = '#E8F0FE'
BACKGROUND = '#FFFFFF'
SURFACE = '#F8F9FA'
TEXT_PRIMARY = '#202124'
TEXT_SECONDARY = '#5F6368'
BORDER = '#DADCE0'
SUCCESS = '#34A853'
WARNING = '#FBBC04'
ERROR = '#EA4335'
CHIP_BG = '#E8EAED'

TAB10_HEX = [
    '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
    '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
]

STYLESHEET = f"""
QMainWindow, QWidget {{
    background-color: {BACKGROUND};
    color: {TEXT_PRIMARY};
    font-family: "Segoe UI", "Roboto", sans-serif;
    font-size: 13px;
}}

/* ---- Toolbar ---- */
#toolbar {{
    background-color: {SURFACE};
    border-bottom: 1px solid {BORDER};
}}

/* ---- Section titles ---- */
QLabel#sectionTitle {{
    font-size: 11px;
    font-weight: 600;
    color: {TEXT_SECONDARY};
    text-transform: uppercase;
    letter-spacing: 1px;
    padding: 12px 0 4px 0;
}}

/* ---- Primary button ---- */
QPushButton#primaryBtn {{
    background-color: {PRIMARY};
    color: white;
    border: none;
    border-radius: 6px;
    padding: 10px 24px;
    font-size: 14px;
    font-weight: 600;
    min-height: 36px;
}}
QPushButton#primaryBtn:hover {{
    background-color: {PRIMARY_HOVER};
}}
QPushButton#primaryBtn:disabled {{
    background-color: {BORDER};
    color: {TEXT_SECONDARY};
}}

/* ---- Secondary / flat button ---- */
QPushButton#flatBtn {{
    background-color: transparent;
    color: {PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 6px 16px;
    font-size: 12px;
}}
QPushButton#flatBtn:hover {{
    background-color: {PRIMARY_LIGHT};
}}

/* ---- Help button (circle) ---- */
QPushButton#helpBtn {{
    background-color: {SURFACE};
    color: {PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 14px;
    font-size: 14px;
    font-weight: 700;
    padding: 0;
}}
QPushButton#helpBtn:hover {{
    background-color: {PRIMARY};
    color: white;
    border-color: {PRIMARY};
}}

/* ---- Progress bar ---- */
QProgressBar {{
    border: 1px solid {BORDER};
    border-radius: 4px;
    text-align: center;
    background-color: {SURFACE};
    min-height: 20px;
    font-size: 11px;
}}
QProgressBar::chunk {{
    background-color: {PRIMARY};
    border-radius: 3px;
}}
QProgressBar[error="true"]::chunk {{
    background-color: {ERROR};
}}

/* ---- Tab bar ---- */
QTabWidget::pane {{
    border: 1px solid {BORDER};
    border-top: none;
    background: {BACKGROUND};
}}
QTabBar::tab {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-bottom: none;
    padding: 8px 20px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    color: {TEXT_SECONDARY};
    font-size: 13px;
}}
QTabBar::tab:selected {{
    background: {BACKGROUND};
    color: {PRIMARY};
    font-weight: 600;
    border-bottom: 2px solid {PRIMARY};
}}
QTabBar::tab:hover:!selected {{
    background: {PRIMARY_LIGHT};
}}

/* ---- Cards ---- */
QFrame#card {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 16px;
}}

/* ---- Stat value ---- */
QLabel#statValue {{
    font-size: 28px;
    font-weight: 700;
    color: {PRIMARY};
}}
QLabel#statLabel {{
    font-size: 11px;
    color: {TEXT_SECONDARY};
}}

/* ---- Tables ---- */
QTableWidget {{
    gridline-color: {BORDER};
    border: 1px solid {BORDER};
    border-radius: 4px;
    selection-background-color: {PRIMARY_LIGHT};
    selection-color: {TEXT_PRIMARY};
    alternate-background-color: {SURFACE};
    font-size: 12px;
}}
QTableWidget::item {{
    padding: 4px 8px;
}}
QHeaderView::section {{
    background-color: {SURFACE};
    border: none;
    border-bottom: 2px solid {BORDER};
    padding: 6px 8px;
    font-weight: 600;
    font-size: 11px;
    color: {TEXT_SECONDARY};
}}

/* ---- Scroll area ---- */
QScrollArea {{
    border: none;
}}

/* ---- Line edits ---- */
QLineEdit, QSpinBox, QDoubleSpinBox {{
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 6px 10px;
    background: {BACKGROUND};
    font-size: 13px;
}}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {PRIMARY};
}}

/* ---- Group box ---- */
QGroupBox {{
    border: 1px solid {BORDER};
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 20px;
    font-weight: 600;
    font-size: 12px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: {TEXT_SECONDARY};
}}

/* ---- List widget ---- */
QListWidget {{
    border: 1px solid {BORDER};
    border-radius: 4px;
    background: {BACKGROUND};
    font-size: 12px;
}}
QListWidget::item {{
    padding: 4px 8px;
}}
QListWidget::item:selected {{
    background-color: {PRIMARY_LIGHT};
    color: {TEXT_PRIMARY};
}}

/* ---- Tooltip ---- */
QToolTip {{
    background-color: {TEXT_PRIMARY};
    color: white;
    border: none;
    padding: 6px 10px;
    border-radius: 4px;
    font-size: 12px;
}}
"""
