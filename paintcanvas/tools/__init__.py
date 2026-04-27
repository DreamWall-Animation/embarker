from paintcanvas.tools.basetool import NavigationTool
from paintcanvas.tools.erasertool import EraserTool
from paintcanvas.tools.movetool import SelectionTool, MoveTool
from paintcanvas.tools.painttool import DrawTool, SmoothDrawTool
from paintcanvas.tools.shapetool import RectangleTool, ArrowTool, CircleTool, LineTool
from paintcanvas.tools.texttool import TextTool
from paintcanvas.tools.transform import TransformTool
from paintcanvas.tools.wipestool import WipesTool


TOOLS = [
{
    'name': 'Navigation',
    'tool': NavigationTool,
    'icon': 'hand.png'
},
{
    'name': 'Move',
    'tool': MoveTool,
    'icon': 'move.png'
},
{
    'name': 'Transform',
    'tool': TransformTool,
    'icon': 'transform.png'
},
{
    'name': 'Selection',
    'tool': SelectionTool,
    'icon': 'selection.png'
},
{
    'name': 'Draw',
    'tool': DrawTool,
    'icon': 'freehand.png'
},
{
    'name': 'Smooth Draw',
    'tool': SmoothDrawTool,
    'icon': 'smoothdraw.png'
},
{
    'name': 'Eraser',
    'tool': EraserTool,
    'icon': 'eraser.png'
},
{
    'name': 'Line',
    'tool': LineTool,
    'icon': 'line.png'
},
{
    'name': 'Rectangle',
    'tool': RectangleTool,
    'icon': 'rectangle.png'
},
{
    'name': 'Circle',
    'tool': CircleTool,
    'icon': 'circle.png'
},
{
    'name': 'Arrow',
    'tool': ArrowTool,
    'icon': 'arrow.png'
},
{
    'name': 'Text',
    'tool': TextTool,
    'icon': 'text.png'
},
]
