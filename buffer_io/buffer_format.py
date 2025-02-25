'''
To the future MMT design:

1. The old 3Dmigoto ib and vb formats cannot import shape key Buffer data into Blender with one click,
nor can they intuitively integrate commonly used BoneMatrix technology and PositionMatrix technology files.

2. Every time you extract from the FrameAnalysis folder, you have to convert the separated Buffer files into .ib .vb .fmt files to import into Blender.
Every time you export, you have to split the ib vb fmt files into buffer files, which is meaningless.

Isn't this fusion and splitting redundant?

So can we skip this fusion and splitting process? Why must we use DrakStarSword's original design? It is obvious that for game mod production,
if the Blender plugin can directly import and export Buffers, it can reduce this extra splitting work when extracting and generating secondary creation models.
This also allows for more intuitive use of 010Editor to see the contents of each Buffer and facilitates direct Buffer operations.

Just like MMT initially used a similar GIMI collection logic to collect from txt, it was completely misled by the wrong ideas of predecessors. The current Blender plugin design is the same, with problems in the predecessors' design.

So we need to design a new data format. Currently, there are two ideas:
1. Design a .3dm format to put all the data in, so there is no need for three different formats: .ib .vb .fmt.
(It seems unnecessary and not easy to maintain, unless the generated Mod also uses this format, but that would require restructuring 3Dmigoto, which is not worth it and not conducive to secondary development by others. It also requires an additional file format parser step, which is not intuitive.)

2. Design a new format.json, so the Blender plugin reads this json file to decide how to import Buffers into Blender for display.

So we ultimately adopt the form of a new format.json + other Buffer files to describe a model's folder.

Therefore, the existing Blender plugin design needs to be completely abandoned and redesigned. The design ideas can refer to WWMI, which does a good job in this regard.

But how to ensure compatibility so that models imported in .ib .vb .fmt format, as well as -ib.txt and -vb0.txt format, can also be supported?
I think as long as the parsing steps from model to file writing are resolved, support for .ib .vb and .txt formats should be provided by other plugins, such as using XXMI, etc.

However, if designed this way, the entire MMT architecture will be completely changed, and the existing MMT logic and Blender plugin logic will need to be rewritten.
But since D3D11 and the subsequent commonly used D3D12 will generally use Buffer format, designing a new general Buffer format is entirely worthwhile.

The main issue is whether 3Dmigoto is really worth it? Its usage range is too small, with only a few games supporting GPU-PreSkinning, but it can be expected that future games will support GPU-PreSkinning.
Moreover, in the future, there will definitely be general GPU-PreSkinning bone fusion frameworks, shape key frameworks, and ComputeShader recalculation bone pose frameworks, etc.
The design should consider future support for other tools that support Buffer replacement, so the design based on Buffer and json description files is entirely feasible and backward compatible.

So it's decided, we will proceed with format changes towards a more general and compatible direction: future-oriented program design...
This decision may not show results in the short term, but within 3 to 5 years, when GPU computing power breaks through, when DX12 is fully popularized, and when DX12Buffer Mod tools based on the ReShade architecture emerge, the current cumbersome preparation and restructuring work of MMT will be worth it.
Decide to spend 1 to 2 days each month for updates, turning it into long-term technical development, betting that future GPUs can indeed achieve the capabilities I am currently speculating.
'''
