from paintcanvas.tools.base import NavigationScrubTool
from paintcanvas.tools.eraser import EraserTool
from paintcanvas.tools.paint import DrawTool, SmoothDrawTool
from paintcanvas.tools.rotate import RotationTool
from paintcanvas.tools.shape import RectangleTool, ArrowTool, CircleTool, LineTool
from paintcanvas.tools.translate import SelectionTool, TranslationTool
from paintcanvas.tools.text import TextTool
from paintcanvas.tools.transform import TransformTool
from paintcanvas.tools.wipes import WipesTool


TOOLS = [
{
    'name': 'Navigation',
    'tool': NavigationScrubTool,
    'shortcut': 'N',
    'icon': 'hand.png'
},
{
    'name': 'Translate',
    'shortcut': 'Z',
    'tool': TranslationTool,
    'icon': 'move.png'
},
{
    'name': 'Rotate',
    'shortcut': 'R',
    'tool': RotationTool,
    'icon': 'rotate.png'
},
{
    'name': 'Transform',
    'shortcut': 'T',
    'tool': TransformTool,
    'icon': 'transform.png'
},
{
    'name': 'Selection',
    'shortcut': 'S',
    'tool': SelectionTool,
    'icon': 'selection.png'
},
{
    'name': 'Draw',
    'shortcut': 'B',
    'tool': DrawTool,
    'icon': 'freehand.png'
},
{
    'name': 'Smooth Draw',
    'shortcut': 'V',
    'tool': SmoothDrawTool,
    'icon': 'smoothdraw.png'
},
{
    'name': 'Eraser',
    'shortcut': 'E',
    'tool': EraserTool,
    'icon': 'eraser.png'
},
{
    'name': 'Line',
    'shortcut': 'L',
    'tool': LineTool,
    'icon': 'line.png'
},
{
    'name': 'Rectangle',
    'shortcut': 'Y',
    'tool': RectangleTool,
    'icon': 'rectangle.png'
},
{
    'name': 'Circle',
    'shortcut': 'C',
    'tool': CircleTool,
    'icon': 'circle.png'
},
{
    'name': 'Arrow',
    'shortcut': 'A',
    'tool': ArrowTool,
    'icon': 'arrow.png'
},
{
    'name': 'Text',
    'shortcut': 'CTRL+T',
    'tool': TextTool,
    'icon': 'text.png'
},
]
