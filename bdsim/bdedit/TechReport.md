bdedit was developed by a QUT computer science student project team.  The following is the final report of that student project.  Significant
subsequent work has been on this tool since the project completed.

# BdEdit Technical Report

Contact Details

Developers

Samara - Email: samara.barwick@connect.qut.edu.au

Rory - Email: rory.higgins@connect.qut.edu.au

John - Email: john.wishart@connect.qut.edu.au

Daniel - Email: daniel.petkov@connect.qut.edu.au

Supervisor

Professor Peter Corke - GitHub: https://github.com/petercorke

# Table of Contents
1. [Context](#h1)

2. [Feature Exploration of Bdedit](#h2)

    [Interface](#h2-sh1)

    [Adding Blocks](#h2-sh2)

    [Sockets](#h2-sh3)

    [Socket Flipping](#h2-sh4)

    [Further Block Manipulation](#h2-sh5)

    [Wires](#h2-sh6)

    [Connector Block](#h2-sh7)

    [Intersection Management](#h2-sh8)

    [Editing Block Parameters](#h2-sh9)

    [Screenshot](#h2-sh10)

    [Grid Mode](#h2-sh11)

    [Grid Snapping](#h2-sh12)

    [Saving and Loading](#h2-sh13)

3. [Class Architecture (High Level)](#h3)

    [1) The Interface Class](#h3-sh1)

    [2) The Scene Class](#h3-sh2)

    [3) The GraphicsView Class](#h3-sh3)

    [4) The Block Class](#h3-sh4)

    [5) The Socket Class](#h3-sh5)

    [6) The Wire Class](#h3-sh6)

4. [Making changes to code](#h4)

    [Adding more blocks types to application](#h4-sh1)

    [Block parameters explained](#h4-sh1)

    [JSON file structure outline](#h4-sh2)

    [How icons were created](#h4-sh3)

    [Procedure for updating changes to existing icons, or adding new ones](#h4-sh4)

5. [Appendices](#h5)

    [APPENDIX A – High Level Class Architecture Diagram](#h5-sh1)

    [APPENDIX B – Stepped Wire Drawing Logic](#h5-sh2)

    [Embedded Links](#h5-sh3)

# 1. Context<a id="h1"></a>

In engineering, complex systems are often represented with block diagrams (refer to Figure 1.1), where blocks represent functions with inputs and outputs, and wires represent the flow of values between the ports of these functions.

<p align="center"><img width="500" alt="Example of System as a Block Diagram" src="https://raw.githubusercontent.com/petercorke/bdsim/bdedit/bdsim/bdedit/figs/Figure_1.1-Example_of_System_as_a_Block_Diagram.png"/></p>

These block diagrams can be modelled and simulated as code through the bdsim [[1]](#h5-sh3-item1) Python package developed by Professor Peter Corke, where the blocks and wires are represented in terms of Python class and method calls.

To aid with the conceptualization of the developed block diagram model and its modelling process, the bdedit package was developed as an addition to bdsim, allowing for block diagrams to be created graphically with items that visually represent the blocks, in/out ports and the wires (refer to Figure 1.2). Bdedit supports the saving and loading of these diagrams to and from a JSON file, which stores all the necessary data for the diagram to later be simulated through bdsim.

<p align="center"><img width="800" alt="Example of Block Diagram as represented in bdedit" src="https://raw.githubusercontent.com/petercorke/bdsim/bdedit/bdsim/bdedit/figs/Figure_1.2-Example_of_Block_Diagram_as_represented_in_bdedit.png"/></p>

# 2. Feature Exploration of Bdedit<a id="h2"></a>
## Interface<a id="h2-sh1"></a>
Installing the bdsim package and its necessary files, then running the bdedit&#46;py [[2]](#h5-sh3-item2) file, launches a new window containing a graphical user interface (refer to Figure 2.1). This interface contains three areas of focus, the canvas (grey grid space), the library browser panel, and the toolbar.

<p align="center"><img width="500" alt="Bdedit Graphical User Interface" src="https://raw.githubusercontent.com/petercorke/bdsim/bdedit/bdsim/bdedit/figs/Figure_2.1-Bdedit_Graphical_User_Interface.png"/></p>

## Adding Blocks<a id="h2-sh2"></a>
Through this interface, the user can create a block diagram by choosing from a list of available blocks found within the Library Browser panel. These will call on the classes related to those blocks, to create a block which both stores its values internally within the program and graphically represents that block within the diagram. The graphical information of these blocks and wires is then stored within the canvas area (refer to Figure 2.2).

<p align="center"><img width="500" alt="Adding Blocks to Canvas and Connecting them" src="https://raw.githubusercontent.com/petercorke/bdsim/bdedit/bdsim/bdedit/figs/Figure_2.2-Adding_Blocks_to_Canvas_and_Connecting_them.png"/></p>

## Sockets<a id="h2-sh3"></a>
These blocks have sockets, representing its inputs and outputs. These are determined through the block type, with some blocks only having input sockets (sink blocks or INPORT blocks), some only having output sockets (source blocks or OUTPORT blocks), and others having both input and output sockets (function, transfer, discrete or SUBSYSTEM blocks) (refer to Figure 2.3).

<p align="center"><img width="400" alt="Examples of Blocks" src="https://raw.githubusercontent.com/petercorke/bdsim/bdedit/bdsim/bdedit/figs/Figure_2.3-Examples_of_Blocks.png"/></p>

These sockets can be used to connect the output of one block to one or more other blocks, creating a flow of data. The following logic is applied to these sockets based on their types:

* Sockets cannot connect to the same socket type (Output cannot connect to Output, Input cannot connect to Input)

* Input sockets can only have one wire connecting into them (any further wires that are connected will be disconnected until the existing wire is removed)

* Output sockets can have any number of wires connected to them

## Socket Flipping<a id="h2-sh4"></a>
Blocks can also be flipped, reversing the sides on which the input and output sockets are located. This can be achieved through pressing the 'F' key (F for flip). These are only graphically updated and do not impact the flow of logic to those sockets (refer to Figure 2.4).

<p align="center"><img width="400" alt="Example of Flipping Socket Orientation" src="https://raw.githubusercontent.com/petercorke/bdsim/bdedit/bdsim/bdedit/figs/Figure_2.4-Example_of_Flipping_Socket_Orientation.png"/></p>

## Further Block Manipulation<a id="h2-sh5"></a>
Blocks can also be selected/ moved and deleted as desired. All items are restriced to being moved around within the borders of the canvas. Wires can also be selected and deleted, but not moved. Sockets cannot be selected, moved or deleted through mouse interaction. Selecting, or rather clicking on, a socket creates a draggable wire. As the block is moved, so too are its sockets. The only instance where sockets move relative to the block, is when the number of input or output sockets changes (which is controlled through the [parameter window](#h2-sh9)).

The selection of an item is indicated by a colour change. When a block, connector block or wire is selected, its outline changes from a thin black line, to a thicker bright orange outline (refer to Figure 2.5).

<p align="center"><img width="300" alt="Block and Wire Selected" src="https://raw.githubusercontent.com/petercorke/bdsim/bdedit/bdsim/bdedit/figs/Figure_2.5-Block_and_Wire_Selected.png"/></p>

As mentioned above, blocks and wires can be deleted when desired. This is done through first selecting the item, then pressing either the 'Backspace' or the 'Del' keys on the keyboard. If a wire is deleted, only the wire will be removed. If a block is deleted, any wires that were connected to it will also be deleted with the block.

## Wires<a id="h2-sh6"></a>
Blocks can be connected to one another by either clicking on a socket of one block, then clicking on a socket of another block, or by click-and-dragging from one socket and releasing over the socket of another block (refer to Figure 2.6). When a wire is connected between two points, wire logic will be applied to it, in order to determine the path it should take to connect those two blocks. Moving the block around once the wire is connected, will update the position of the wire end points, and as such, will cycle through the wire logic to determine what path the wire should follow (refer to [APPENDIX B](#h5-sh2) for examples and a walkthrough of this logic).

<p align="center"><img width="600" alt="Example of Dragging Wire" src="https://raw.githubusercontent.com/petercorke/bdsim/bdedit/bdsim/bdedit/figs/Figure_2.6-Example_of_Dragging_Wire.png"/></p>

## Connector Block<a id="h2-sh7"></a>
The sections of the wires cannot be pulled out and positioned to the user's liking, as their path is solely dependent on the position of the two points it connects. Hence, to assist with routing the wires when the diagrams become more complex with wires travelling in multiple directions, a connector block can be used as an intermediary point through which the wire must travel. These provide the user with more control over how the wire travels between any two points, by creating more points in between the start and end point, which the wire must first connect. The comparison between using a connector block and not, can be seen in Figure 2.7. The connect block appears as a single Input and Output socket joined together on one edge; and similarly to other blocks, it is also flip-able.

<p align="center"><img width="600" alt="Usage of Connector Blocks" src="https://raw.githubusercontent.com/petercorke/bdsim/bdedit/bdsim/bdedit/figs/Figure_2.7-Usage_of_Connector_Blocks.png"/></p>

## Intersection Management<a id="h2-sh8"></a>
As seen in the bottom part of Figure 2.7, wires can overlap at times, and although they are fairly easy to follow in this figure, it can become difficult to follow the flow of logic when the diagram becomes more complex. To address this problem area, parts of wires that cross over each other can be separated to indicate they do not cross, but instead pass over each other (refer to Figure 2.8). This feature might not always be desired, so it has been disabled by default, however can be toggled on or off by the user through pressing the 'I' key (I for intersection). The wire logic at these intersection points, keeps all vertical segments of wires solid, and erases parts of any horizontal segments that they pass through.

<p align="center"><img width="700" alt="Toggling Wire Intersection Detection ON" src="https://raw.githubusercontent.com/petercorke/bdsim/bdedit/bdsim/bdedit/figs/Figure_2.8-Toggling_Wire_Intersection_Detection_ON.png"/></p>

## Editing Block Parameters<a id="h2-sh9"></a>
Integral to the creation and simulation of block diagrams, is the ability to edit the parameter values related to each block, as this dictates what output value a block produces and how blocks process any inputs that feed into it to produce an output. If supported for the given block, it is also possible to edit the number of input or output sockets a block has. All blocks (aside from connector blocks) can be named as desired by the user. As blocks are spawned they are given a default name which is auto incremented depending on the block type.

These user-editable block parameters are editable through a Parameter Window panel that appears on the right hand side of the screen when triggered to do so (refer to Figure 2.9). It can be toggled to open by first selecting a block, then right clicking the mouse; subsequently, it can be closed at any moment by either right clicking again or left clicking anywhere in the screen. Closing the Parameter Window will retain any values that have been edited, but will only update the block parameters once the 'Updated Parameters' button has been clicked.

<p align="center"><img width="600" alt="Parameter Window" src="https://raw.githubusercontent.com/petercorke/bdsim/bdedit/bdsim/bdedit/figs/Figure_2.9-Parameter_Window.png"/></p>

When parameters are edited and the user selects update, all editable values within the Parameter Window will be checked to ensure they adhere to the conditions placed on them. If the block title is changed, this will be checked against other existing block titles, to ensure the name of the current block would not be a duplicate. If the block parameters are changed, they will be compared against their required types to ensure they match (e.g. float, int, bool, list, str), and if any further restrictions are placed on these parameters (e.g. matching to certain strings, or being within a certain range), they will be checked against those too. This information is defined internally within the block class, and applied to the block when it is created.

User feedback pop-up windows are also connected to this Parameter Window. If the user provides values that are incorrect - be they a duplicate block title, incorrect types or not adhering to further restrictions – the block parameters will not be updated, and an error message will be displayed notifying the user with useful information for where the issue occurred. If all values are correctly inputted, a success message will be displayed in the same area (refer to Figure 2.10).

<p align="center"><img width="700" alt="User-Feedback Messages" src="https://raw.githubusercontent.com/petercorke/bdsim/bdedit/bdsim/bdedit/figs/Figure_2.10-User-Feedback_Messages.png"/></p>

## Screenshot<a id="h2-sh10"></a>
Upon creating a block diagram, the user can take a screenshot of all items within the canvas by simply pressing the 'Screenshot' button located within the toolbar. This will save a 4k resolution image of the entire canvas and everything in it. This resolution is chosen due to canvas size potentially being 5x the desktop screen size due to the zooming feature. Due to limited time to further develop this feature, at present time, this image will be saved with the '.png' file extension, under the name 'Scene Picture' in the same folder the interface is run from. **If taking multiple screenshots this way, be aware that this will override any previous screenshot you may have taken.**

## Grid Mode<a id="h2-sh11"></a>
To improve the viewing quality of the screenshots taken, and reduce the amount of visual noise/messiness created by having the background be a grid, an option is available from the toolbar to disable the background by navigating to the 'Grid Mode" button in the toolbar, and selecting 'Off' from the drop down menu. Alternatively, the grid can be displayed in two other modes, Light (the default mode) and Dark (refer to Figure 2.11).

<p align="center"><img width="1400" alt="Background Colour Modes" src="https://raw.githubusercontent.com/petercorke/bdsim/bdedit/bdsim/bdedit/figs/Figure_2.11-Background_Colour_Modes.png"/></p>

## Grid Snapping<a id="h2-sh12"></a>
To improve the usability of the interface and the user experience when moving/aligning blocks within the canvas, a grid snapping feature has been implemented, where movement of the mouse will be restricted to moving the block in increments of 20 pixels (the width of the smaller grid squares). Additionally, all sockets are indexed in increments of the same value (20 pixels) in order to line up with these smaller grid lines. As such, since wires are automatically drawn between the socket positions, it is much easier to move blocks around in order to make them straight.

## Saving and Loading<a id="h2-sh13"></a>
An integral component to this bdedit tool is the support for saving the current progress made on a block diagram, and the support to load a previously worked on block diagram (provided it is in a compatible format). Block diagrams are saved as JSON files, containing information about the canvas size, all the blocks (its name, on-screen position, parameters, and sockets), and finally all the wires and the sockets they connect to. This information is stored as a dictionary within the JSON file, which is parse-able as key-value pairs, where the key represents the name of the variable or parameter related to the scene, block, socket or wire, and the value representing the value that variable holds.

A file can be saved or loaded from through the associated 'Save' or 'Save As' and 'Load' buttons within the toolbar. Upon clicking on one of these buttons, the a file browser window will pop up (allowing the user to browse their devices' file structure), prompting the user to either select a file to load or to choose the location they wish for their file to be saved (and the name of the file if it's the first time saving or if saving the diagram as a new file).

Due to a limitation of time to further develop this feature, whether this file is in a compatible format is not checked before it is attempted to be parsed, so any errors that may occur due to an incorrect file being loaded, will result in the crashing of the bdedit tool.

# 3. Class Architecture (High Level)<a id="h3"></a>
 The architecture of BDEdit can be summarize through the connectivity between 6 main classes as seen in Figure 3.1. Other classes are also essential, however it is through the interactions between these 6 main classes that the application is able to run. For a full size image of this architecture refer to [APPENDIX A](#h5-sh1). These classes break down into the following:

<p align="center"><img width="300" alt="Bdedit Architecture Diagram" src="https://raw.githubusercontent.com/petercorke/bdsim/bdedit/bdsim/bdedit/figs/Figure_3.1-BdEdit_Architecture_Diagram.png"/></p>

### 1) <span style="color:#EA503B">**The Interface Class**</span><a id="h3-sh1"></a> – 
This class is responsible for the dimensions of the BDEdit window that appears when the application is run, as well as managing the layout of where all the interact-able areas of the application are, these being:
* The toolbar;

* The left side panel (otherwise named the Library Browser);

* The right side panel (otherwise named the Parameter Window); and

* The canvas or work-area (which is an instance of the <span style="color:#EC872D">GraphicsScene</span> class, who itself is a child class of the <span style="color:#EC872D">Scene</span> class, AND is connected to a <span style="color:#EC872D">GraphicsView</span> class instance).

It is namely the creation of the <span style="color:#EC872D">GraphicsScene</span> class that allows for the graphical representation of <span style="color:#4E9FD8">Blocks</span>, <span style="color:#7ABA50">Sockets</span> and <span style="color:#957597">Wires</span>, the culmination of which allows for the making of a Block Diagram.

### 2) <span style="color:#EC872D">**The Scene Class**</span><a id="h3-sh2"></a> – 
This class is responsible for three things.

* Storing all instances of any Wires and Blocks (and their <span style="color:#7ABA50">Sockets</span>) that are created, i.e. their structures, internal variables, lists, properties, etc. It also manages the adding/removing of these instances.

* Creating and storing a <span style="color:#EC872D">GraphicsScene</span> class instance, in which all the <span style="color:#4E9FD8">GraphicsBlock</span>, <span style="color:#7ABA50">GraphicsSocket</span>, and <span style="color:#957597">GraphicsWire</span> class instances are added to graphically represent their class respectively. This allows for the all the relevant internal information of the <span style="color:#4E9FD8">Block</span>, <span style="color:#7ABA50">Socket</span> and <span style="color:#957597">Wire</span> classes to be represented graphically!

* Managing the intersection points at which any two (or more) wires overlap.

### 3) <span style="color:#EC872D">**The GraphicsView Class**</span><a id="h3-sh3"></a> – 
This class instance is connected to the <span style="color:#EC872D">GraphicsScene</span> through the <span style="color:#EA503B">Interface</span> class, and is responsible for monitoring the <span style="color:#EC872D">GraphicsScene</span> and implementing logic to any user interactions within it. These interactions being: key presses, mouse press/release, mouse movement, scroll click and scroll movement events. These detected events are caught in real time, allowing for logic within the GraphicsScene to also be updated in real time. Some examples of this includes:

* the creation of a <span style="color:#957597">Wire</span> (and subsequent <span style="color:#957597">GraphicsWire</span>) when a <span style="color:#7ABA50">GraphicsSocket</span> is clicked on;

* the real-time updates to how the <span style="color:#957597">GraphicsWire</span> is drawn while being pulled from one <span style="color:#7ABA50">GraphicsSocket</span> to another;

* the real-time updates to how the <span style="color:#4E9FD8">GraphicsBlock</span> is drawn when the number of sockets on it changes, or when it is selected;

* the zooming in and out of, and panning of the canvas (<span style="color:#EC872D">GraphicsScene</span>).

### 4) <span style="color:#4E9FD8">**The Block Class**</span><a id="h3-sh4"></a> – 
An instance of this class is created when a respective button is clicked from the Library Browser side panel in the Interface. This class is responsible for holding all <span style="color:#4E9FD8">Block</span> related variables, these beings things like its name, position within the canvas, block type, icon, dimensions, user-editable parameters and a list of input and output <span style="color:#7ABA50">Socket</span> instances that are related to this <span style="color:#4E9FD8">Block</span>. Additionally, this class relates and instance of the **ParamWindow** class and <span style="color:#4E9FD8">GraphicsBlock</span> class to this <span style="color:#4E9FD8">Block</span>.

The **ParamWindow** is a class which creates a Parameter Window in which are displayed this <span style="color:#4E9FD8">Blocks'</span> type, title and user-editable parameters, and through which a user can edit the parameters of a given block. When this Parameter Window is opened, it appears in a right side panel within the <span style="color:#EA503B">Interface</span>.

Similar to how the <span style="color:#EC872D">GraphicsScene</span> represents a <span style="color:#EC872D">Scene</span> class instance, the <span style="color:#4E9FD8">GraphicsBlock</span> graphically represents a given <span style="color:#4E9FD8">Block</span>, and sends that graphical information to the <span style="color:#EC872D">GraphicsScene</span> to display.

### 5) <span style="color:#7ABA50">**The Socket Class**</span><a id="h3-sh5"></a> –
An instance of this class is created and connected to a <span style="color:#4E9FD8">Block</span>, whenever one is made. This class is responsible for holding all <span style="color:#7ABA50">Socket</span> related variables, like its index (from the top of the <span style="color:#4E9FD8">Block</span>, these are auto incremented as more <span style="color:#7ABA50">Socket</span> are made for a Block), the position to be drawn at (Left or Right of the <span style="color:#4E9FD8">Block</span>), the type of <span style="color:#7ABA50">Socket</span> being drawn (Input or Output) and finally a list of all <span style="color:#957597">Wires</span> that are connected to this <span style="color:#7ABA50">Socket</span>.

Additionally, some special blocks (PROD and SUM Blocks) have math operators (+,-,×,&#xf7;) drawn alongside their input Sockets depending on what string for one of those block's parameters. For example, that parameter may be the string "`*/*`" in the PROD block, and this will draw a '×', '&#xf7;', '×' alongside the first, second, third input sockets respectively.

The <span style="color:#7ABA50">Socket</span> class also holds an instance of <span style="color:#7ABA50">GraphicsSocket</span> which graphically represents the <span style="color:#7ABA50">Socket</span>, and is sent to the <span style="color:#EC872D">GraphicsScene</span> to be drawn.

### 6) <span style="color:#957597">**The Wire Class**</span><a id="h3-sh6"></a> – 
As was mentioned in the <span style="color:#EC872D">GraphicsView</span>, when it has detected that a <span style="color:#7ABA50">GraphicsSocket</span> has been clicked, this will create a <span style="color:#957597">Wire</span> instance from that <span style="color:#7ABA50">Socket</span>, and a subsequent <span style="color:#957597">GraphicsWire</span> from the <span style="color:#7ABA50">GraphicsSocket</span> to the mouse cursor, until either the <span style="color:#957597">GraphicsWire</span> is clicked off of into an empty space within the <span style="color:#EC872D">GraphicsScene</span>, or the wire is clicked off of onto another <span style="color:#7ABA50">GraphicsSocket</span>. If these socket types are different (i.e. both aren't input or output sockets), then the wire is connected and will remain so, even as the <span style="color:#4E9FD8">GraphicsBlock</span> is moved around. The <span style="color:#957597">Wire</span> class is responsible for holding all <span style="color:#957597">Wire</span> related variables, these being what <span style="color:#7ABA50">Sockets</span> this <span style="color:#957597">Wire</span> connects (start/end sockets) and the type of wire being drawn (Direct, Bezier or Step). The wire type dictates the style with which the wire is drawn. Direct draws the wire as a straight line between two points. Bezier draws the wire as a cubic between two points (think sinusoidal wave). Step draws a wire with 90 degree bends at each point the wire must turn to reach the end socket.

Although other methods and classes are involved in the process of making this application meet further functional requirements, these 6 classes are what tie everything together.

# 4. Making changes to code<a id="h4"></a>
<a id="h4-sh1"></a>

## Adding more blocks types to application
If the new block type falls under one of the following, already existing categories: Source, Sink, Function, Transfer, Discrete, INPORT, OUTPORT or SUBSYSTEM block (these last three are located within the hierarchy file), then that block simply needs to be added as a class of one of the Python files relating to those block types. These Python files are located in the "**_`bdsim/bdsim/bdedit/Block_Classes`_**" folder (refer to Figure 4.1), with the names seen in Figure 4.2.

<p align="center" float="middle">
<img width="400" alt="Relevant bdsim File Structure" src="https://raw.githubusercontent.com/petercorke/bdsim/bdedit/bdsim/bdedit/figs/Figure_4.1-Relevant_bdsim_File_Structure.png"/>


<img width="200" alt="Block Type Files" src="https://raw.githubusercontent.com/petercorke/bdsim/bdedit/bdsim/bdedit/figs/Figure_4.2-Block_Type_Files.png"/>
</p>

Within each of those files, the first few lines import the block type they inherit, for example, the "**_`block_function_blocks.py`_**" file imports the FunctionBlock class from the "**_`block.py`_**" file (located in "**_`bdsim/bdsim/bdedit`_** ") inheriting its properties. An example of one of the blocks within these files (without the block comments) is given below:

``` python
class Function(FunctionBlock): 
    def __init__(self, 
                 scene, 
                 window, 
                 func="Provide Function", 
                 nin=1, 
                 nout=1, 
                 dictionary=False, 
                 args=(), 
                 kwargs={}, 
                 name="Function Block", 
                 pos=(0, 0)): 

        super().__init__(scene, window, name, pos)

        self.setDefaultTitle(name)

        self.block_type = blockname(self.__class__)

        self.parameters = [ 
            ["func", str, func, []], 
            ["nin", int, nin, [["range", [0, 1000]]]], 
            ["nout", int, nout, [["range", [0, 1000]]]], 
            ["dict", bool, dictionary, []], 
            ["args", tuple, args, []], 
            ["kwargs", dict, kwargs, []] 
        ]

        self.inputsNum = nin 
        self.outputsNum = nout

        self.icon = ":/Icons_Reference/Icons/function.png" 
        self.width = 100 
        self.height = 100

        self._createBlock(self.inputsNum, self.outputsNum)
```

This block class type is constructed based on the definition of the corresponding bdsim block [[3]](#h5-sh3-item3). When adding in a new block, the following template can be copied and adjusted as needed.

``` python
# The name of this new block class should be unique, and
# it should inherit whichever block type it belongs to.
class My_New_Block(Class_the_new_block_relates_to):

    # Next, the scene and window are required to be passed to the
    # creation of this block (and will be done so automatically from
    # the interface). The following input parameters are the parameters
    # of the block and their respective default values.
    # Finally comes the block's default name (if the user doesn't provide
    # one), and the position is set to always spawn the block at the
    # centre of the work area.
    def __init__(self, 
                 scene, 
                 window, 
                 param1="parm1_default_value", 
                 param2="parm2_default_value", 
                 param3="parm3_default_value", 
                 name="My_New_Block Block", 
                 pos=(0, 0)): 
        super().__init__(scene, window, name, pos)

        # The chosen default name for this block is passed to
        # the setDefaultTitle function which will ensure no duplicate
        # names names of this block exist.
        self.setDefaultTitle(name)

        # The block type is set as the given name of this block class
        self.block_type = blockname(self.__class__)

        # The parameters of the block are wrapped into a list, where each
        # parameter sits inside its own list and defines
        # the name, type, default value, and any further restrictions
        # for each respective parameter.
        self.parameters = [ 
            ["parameter 1", str, param1, []], 
            ["parameter 2", str, param2, []], 
            ["parameter 3", str, param3, []] 
        ]

        # The icon file path is matched to whatever name the icon for
        # this block was named within the Icons folder (this procedure
        # will require the icons resource file to be updated for a new
        # image to be findable within this folder).
        self.icon = ":/Icons_Reference/Icons/my_new_block.png"

        # The height and width are set for this block
        self.width = 100 
        self.height = 100

        # Finally the block is created, with the number of input and
        # output sockets that have been assigned to this block. (This
        # will be inherited from the class this block inherits).
        self._createBlock(self.inputsNum, self.outputsNum)
```

This simply needs to be added to the end of the appropriate file (as chosen from Figure 4.2), and this will make the block automatically appear within the interface.

## Block parameters explained<a id="h4-sh2"></a>
Each block has its own unique parameters, with their own unique names, types, default values and further restrictions (like being restricted to a certain range of allowable numbers). All of a given blocks' parameters are stored within the self.parameters variable list, with each individual parameter being stored as a list within the self.parameters list. Each individual parameter is defined with the following format:

* **_parameter = ["name", type, value, [restrictions]]_**
    
    _e.g. parameter = [["Gain", float, gain, []], ["Premul", bool, premul, []]]_

The items which make up this list of the parameter, are as follows:

* **_name_**: _this is the name of the parameter as a string_

* **_type_**: _this is the type this parameter must be (e.g. int, str, float)_

* **_value_**: _this is the default value the parameter will be set to, if no other value is given. It must also adhere to the required type of the parameter._

* **_restrictions_**: _this is a list (can be list of lists) containing further restrictions applied to the parameter._

As multiple restrictions can be applied to a single parameter, each individual restriction is enclosed as a list. If no restrictions are applied to a parameter, the main restrictions list (inside the parameter list) will simply be an empty list, as seen in the example. These restrictions follow the following structure:

* **_restriction = ["restriction name", [condition(s)]]_**
    
    What these two items within the restriction list represent is explained below:

* **_restriction name_** : _can be only one of the following "keywords", "range", "type" or "signs"._

* **_condition(s)_**: _differ based on the restriction name used, and will be of the following format:_

Currently, only the four restriction types mentioned below are recognized. These must be entered as a string in the first item within the restriction list ("restriction name"), to indicate what kind of restriction is being applied to this parameter. Following this first value, a list containing one or more conditions placed on the restriction is defined. These depend on the type of restriction chosen. Examples of these restrictions are given below:

```python
[["keywords", ["sine", "square", "triangle"]]]
```

* This restriction compares the parameter value against the strings defined within the conditions list. This restriction should only be used on parameters whose required type is 'str' (string). If the parameter value doesn't match any of these strings, this will throw an error notifying the user that their input must match one of those strings.

* Here the conditions list is just a list of all the variations the parameter value can be.

```python
[["range", [-math.inf, math.inf]]]
```

* This restriction compares the parameter value against being within a range of given numbers, defined by a min and a max. This restriction should only be used on parameters whose required type is either 'float' or 'int'. If the parameter value is outside the allowable range, this will throw an error notifying the user that their input must be within the given range.

* Here the conditions list simply is made up of a minimum and maximum value.

```python
[["type", [type(None), int, float]]]
```

* This restriction compares the type of the parameter value against one of the additional allowable types for this parameter. If for instance, a parameter can either an integer or a float when defined, or a None type otherwise, this means the parameter can be one of 3 different types, and this restriction allows the parameter to pass as long as its type matches one of the defined types. In order to allow other types, the type set for this parameter (as the second item in the parameters list), must also be included in this conditions list, usually as the last item (for consistency sake). Note, when allowing a parameter to have None as a value, since None isn't a type, but rather a NoneType, type(None) is used to extract the type of None. If the type of the parameter value doesn't match one of the other allowable types, this will notify the user of the error, and the allowable types.

* Here the conditions list is just a list of all the acceptable types for that parameter, with the required type of the parameter also being in that list (usually as the last value in the list; which is float in this case).

```python
[["signs", ["*", "/"]]] or[["signs", ["+", "-"]]]
```

* This restriction compares the parameter value against the various characters that have been defined in the conditions list. This restriction should only be used for SUM and PROD type blocks, as these have input sockets which are labelled according to the signs defined in this condition list. The parameter value for these blocks (SUM and PROD) is entered as a string of characters, and each character for the respective block is checked against the ones that are allowed from the conditions list. If that string is made up of any number of characters that don't match the ones that are allowed, an error will be thrown, notifying the user of the allowable inputs.

* Here the conditions list is just a list of all the allowable characters for that parameter

## JSON file structure outline<a id="h4-sh2"></a>
The JSON file structure contains all the necessary information of the reconstruction of blocks, sockets and wires that exist within a block diagram, and represents them as dictionaries, of key-value pairs which represent the name and value of parameters relevant to those items. All of these items (blocks, sockets, and wires) are contained within a Scene as explained in [Section 3](#Class_Architecture(High), hence they follow the following hierarchy:

* A Scene is represented as dictionary with:

    * Dimensions: these are two parameters of the width and height of the scene.

    * Blocks: this is a list of all the blocks within the diagram, with each block as a dictionary.

    * Sockets: each block has its own unique sockets, so these are stored as part of the block they belong to, also in a list, with each socket as a dictionary.

    * Wires: this is a dictionary list of all the wires within the diagram.

The following block diagram was made to aid with understanding this structure.

<p align="center"><img width="250" alt="Block Diagram Example for JSON File Stucture" src="https://raw.githubusercontent.com/petercorke/bdsim/bdedit/bdsim/bdedit/figs/JSON_file_example_diagram.png"/></p>

There are 3 blocks, created in the order:
1. Function Block – has 1 input socket, 1 output socket
2. Scope Block – has 2 input sockets, no output sockets
3. Constant Block – has no input sockets, 1 output socket

There are also 2 wires, created in the order:

1. Function block -&gt; 1st input socket of Scope Block
2. Constant block -&gt; 2nd input socket of Scope Block

Below, is the resulting JSON file that was generated.

<p align="center">
<img width="1300" alt="JSON File Structure 1" src="https://raw.githubusercontent.com/petercorke/bdsim/bdedit/bdsim/bdedit/figs/JSON_file_example_code_1.PNG"/>
<img width="1300" alt="JSON File Structure 2" src="https://raw.githubusercontent.com/petercorke/bdsim/bdedit/bdsim/bdedit/figs/JSON_file_example_code_2.PNG"/>
</p>

The important points to take away from this JSON structure, is that each block, socket and wire has unique ID's. Although the ID's of the blocks are less useful (can be helpful for differentiating between different blocks of the same time, although their name should be sufficient), the ID's of the sockets are very important. By definition each wire has a start socket and end socket that it is drawn between, and these are referred to by their unique ID. These unique ID's of the sockets, can then be traced back to the block they belong to, hence providing the crucial information of which block connects to which.

As an example, in this block diagram that was made, wire #1 connects the **Function block** from its **output**, to the **1st input** of the **Scope block**. In the wire, these start/end sockets are stored as "start_socket": 2427529113712 and "end_socket": 2427529150816,and if we check the socket id's of the **output socket** of the **Function block**, it is stored as "id": 2427529113712, which we expect to match our "start_socket"(which it does), and doing the same for the **1st input socket** of the **Scope block**, it is stored as "id": 2427529150816, which also matches our ID of the "end_socket".

## How icons were created<a id="h4-sh3"></a>
Icons for bdedit were creating using the free image editing application, paint&#46;net [[4]](#h5-sh3-item4). Paint&#46;net is only compatible with windows operating systems, however there are other options available for image editing applications on Mac or Linux systems.

The sought after properties of image editing tools for creating/editing these icons were: for the ability to create layered images, moving layer position in the layer stack, hiding/showing the layer, selecting parts of images and separating them from the background (leaving only the outline/shape), and more importantly, support for transparent backgrounds.

Paint&#46;net provides support for all these requirements, but other software options may also, so feel free to use whichever software, as long as the final images are saved in '.png' format and have transparent backgrounds. Paint&#46;net also allows for files to be saved in their separate state as layers with the '.pdn' file type, however only Paint&#46;net can open these files. For Windows users this shouldn't be a problem, but for users on other systems, the layers that make up each icon have been saved separately, which will allow them to be added as layers to which ever software is used on those operating systems.

Icons in general, were developed on a 250x250 pixel, transparent background. These dimensions were based off the blocks being 100x100 pixels when drawn within the interface, and the icon being drawn within these blocks having a space of 50x50 pixels to occupy. Having a 250x250 pixel raw icon image allows it to be scaled down to a 50x50 image through PyQt5's scaling tool, which retains the quality of the image better, resulting in it being less pixelated when zoomed in.

The items (text, dividing lines, function lines, etc.) within the icons were positioned with the help of a grid (named "layout_grid.png"), located within the Icons folder in which all the icons are stored. There wasn't a specific method for positioning the items within these icons, but depending on what the icon was (text, shape, axis with function) the lines of the grid were used to symmetrically place items and position them to allow for satisfactory visibility. These icons were developed in monochrome mode (black and white). The following values were used for lines and text:

* linewidth:
    * 6 for axis lines and outline of gain,
    * 8 for bolded thin lines (particularly as dividing lines),
    * 15 for outline of stop icon
    * 19 for function lines (clip, constant, piecewise, step, waveform)
* text font: Calibri
* text size: various amongst the text used, but will be one of the following:
    * 36, 48, 59, 72, 84, 108, 144
* text bolding: True for all text, apart from the stop icon

<a id="h4-sh4"></a>

## Procedure for updating changes to existing icons, or adding new ones

As Python creates some difficulties in accessing absolute or relative file paths, and making this consistent across all users, an alternative available from PyQt5 was used, which is a QReferenceFile.

Similar to zipping files into a folder, this reference file packages image files into a Python importable file, which after importing, can then be accessed locally within the same directory. Hence all icons which were used, were placed into the Icons folder, located at "**_`bdsim/bdsim/bdedit/Icons`_**" folder (see Figure 4.1), and a reference file named " Icons.qrc " was made (following the structure below) in the bdedit package, located at "**_`bdsim/bdsim/bdedit`_**" folder (see Figure 4.1).

In order to make the "**_`.qrc`_**" (resource) file importable and usable in the Python scripts, it must be converted to a "**_`.py`_**" (Python) file (in our case named "**_`Icons.py`_**"). The steps for this procedure will be outlined below.

The following steps should be followed for updating an icon that already exists

1. The new icon (under the same name as the existing icon it's replacing) should be added as a "**_`.png`_**" to the "**_`bdsim/bdsim/bdedit/Icons`_**" folder, replacing the old version of the icon.

2. The "**_Icons.qrc_**" file located at "**_`bdsim/bdsim/bdedit`_**" should be converted to "**_`Icons.py`_**" with the following steps:
    
    1. Via the terminal, navigate to the bdedit directory

    2. Via the terminal, type "**_`pyrcc5 Icons.qrc -o Icons.py`_**" to convert and write the contents of the resource file (named "**_`Icons.qrc`_**") to a Python file (named "**_`Icons.py`_**"). The name of the resource file should match that of what was given to the resource file, and the name of the Python file will be what is called when importing into other Python files (as "**_`from bdsim.bdedit.Icons import *`_**"). DO NOT make any changes to this generated Python file, as this could result in unforeseen errors.

3. Assuming the icon that is being replaced, was previously set up and being used, re-running the program after updating the "**_`Icons.py`_**" file will update the changes made to this icon.

The following steps should be followed for adding in a new icon, that doesn't exist anywhere in the code:

1. The new icon (with a unique name) should be added as a "**_`.png`_**" to the "**_`bdsim/bdsim/bdedit/Icons`_**" folder.

2. The structure of the "**_`Icons.qrc`_**" resource file located at "**_`bdsim/bdsim/bdedit`_**" should be edited to include the file path to this newly added icon. The following steps should be taken:

    1. Open the resource file with any text viewer (should see a file similar to Figure 4.3)

    2. Add the file path to the new icon as "**_`Icons/filename.png`_**" enclosed in the &lt;file&gt; and &lt;/file&gt; tags, indicating that this icon is located within the Icons folder. Note the qresource prefix name; this will be used for picking out specific icons from this file.

    3. Save the resource file and proceed to Step 3.

3. The "**_`Icons.qrc`_**" resource file located at "**_`bdsim/bdsim/bdedit`_**" should be converted to "**_`Icons.py`_**" with the following steps:

    1. Via the terminal, navigate to the bdedit directory

    2. Via the terminal, type "**_`pyrcc5 Icons.qrc -o Icons.py`_**" to convert and write the contents of the resource file (named "**_`Icons.qrc`_**") to a Python file (named "**_`Icons.py`_**"). The name of the resource file should match that of what was given to the resource file, and the name of the Python file will be what is called when importing into other Python files (as "**_`import Icons`_**"). DO NOT make any changes to this generated Python file, as this could result in unforeseen errors.

4. Next, you should open the file where you planned to use the icon (this should be one of the files in either the "**_`bdsim/bdsim/bdedit/Block_Classes`_**" folder or in the "**_`bdsim/bdsim/bdedit`_**" package).

    1. If in any file within the Block_Classes folder, continue to Step 5.

    2. If in any other within the bdedit package: 1. Import the "**_`Icons.py`_**" file from the bdedit package as: "**_`from bdsim.bdedit.Icons import *`_**".

5. Still in the same file as Step 4, continue to the code where you want the Icon file path to be defined and insert the following string: "**_`:/Icons_Reference/Icons/filename.png`_**". The "**_`:/`_**" notation is important for navigating the "**_`Icons.py`_**" file. Also, remember from the note in Step 2, the qreference name is used here as "**_`Icons_Reference`_**" to refer to the "**_`Icons.py`_**" file. The "**_`/Icons/filename.png`_**" points to the path defined in the "**_`Icons.qrc`_**" file. Replace "**_`filename`_**" with whatever name you saved the icon under. 

6. This should complete the process for adding in a new icon.

<p align="center"><img width="700" alt="QResource File Structure" src="https://raw.githubusercontent.com/petercorke/bdsim/bdedit/bdsim/bdedit/figs/Figure_4.3-QResource_File_Structure.png"/></p>

# 5. Appendices<a id="h5"></a>
<a id="h5-sh1"></a>

## APPENDIX A – High Level Class Architecture Diagram

<p align="center"><img width="1600" alt="High Level Class Architecture Diagram" src="https://raw.githubusercontent.com/petercorke/bdsim/bdedit/bdsim/bdedit/figs/APPENDIX_A-High_Level_Class_Architecture_Diagram.png"/></p>

<a id="h5-sh2"></a>

## APPENDIX B – Stepped Wire Drawing Logic
Drawing the step wire falls into three steps of logic.

The first step: when a wire is being pulled from one socket to another, and has not yet been connected.

In this step, the wire is simply drawn as a straight light from the starting socket to the mouse cursor, up until the point the wire is connected to another socket. This is when the wire drawing logic falls into the following two steps of logic.

The second step: Wire routing logic between two blocks where the input and output sockets are on same sides

<p align="center"><img width="1000" alt="Wire Logic Step 2.0" src="https://raw.githubusercontent.com/petercorke/bdsim/bdedit/bdsim/bdedit/figs/APPENDIX_B-Wire_logic_step_2.PNG"/></p>

The third step: Wire routing logic between two blocks where the input and output sockets are on opposite sides

<p align="center"><img width="1000" alt="Wire Logic Step 3.0" src="https://raw.githubusercontent.com/petercorke/bdsim/bdedit/bdsim/bdedit/figs/APPENDIX_B-Wire_logic_step_3.1.PNG"/></p>

<p align="center"><img width="1000" alt="Wire Logic Step 3.1" src="https://raw.githubusercontent.com/petercorke/bdsim/bdedit/bdsim/bdedit/figs/APPENDIX_B-Wire_logic_step_3.2.PNG"/></p>

## Embedded Links<a id="h5-sh3"></a>

<a id="h5-sh3-item1"></a>
1 - https://github.com/petercorke/bdsim

<a id="h5-sh3-item2"></a>
2 - File located at path: https://github.com/petercorke/bdsim/blob/bdedit/bdsim/bin/bdedit.py

<a id="h5-sh3-item3"></a>
3 - https://petercorke.github.io/bdsim/bdsim.blocks.html?highlight=Function#bdsim.blocks.functions.Function

<a id="h5-sh3-item4"></a>
4 - Free paint.net download link - https://www.getpaint.net/download.html#download
