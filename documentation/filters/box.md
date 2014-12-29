This file will contain information about the BoundingBox parameter

## BoundingBoundingBox

### Properties

| Property Name | Description |
| ------------- | ----------- |
| size | The size of the BoundingBox |
| width | The dimension of the BoundingBox along the X axis |
| height | The dimension of the BoundingBox along the Y axis |
| length | The dimension of the BoundingBox along the Z axis |
| minx | The minimum X coordinate in the BoundingBox |
| miny | The minimum Y coordinate in the BoundingBox |
| minz | The minimum Z coordinate in the BoundingBox |
| maxx | The maximum X coordinate in the BoundingBox |
| maxy | The maximum Y coordinate in the BoundingBox |
| maxz | The maximum Z coordinate in the BoundingBox |
| maximum | The largest point located in the BoundingBox |
| volume | The volume of the BoundingBox in blocks |
| positions | Iterates through all the coordinates in the BoundingBox |
| mincx | Smallest X chunk position in the BoundingBox |
| mincz | Smallest Z chunk position in the BoundingBox |
| maxcx | Largest X chunk position in the BoundingBox |
| maxcz | Largest Z chunk position in the BoundingBox |
| chunkPositions | Iterates through all chunk positions in the BoundingBox |
| chunkCount | The amount of chunks in the BoundingBox |
| isChunkAligned | Whether the BoundingBox is aligned with chunk borders |

### Functions

| Function Name | Arguments | Description |
| ------------- | --------- | ----------- |
| intersect | BoundingBox=BoundingBoundingBox | Returns the area contained by both BoundingBoxes, will have zero volume if no area is shared |
| union | BoundingBox=BoundingBoundingBox | Returns a BoundingBox that is large enough to contain both BoundingBoxes |
| expand | dx=Integer, dy=Integer, dz=Integer | Returns a BoundingBox that is expanded by  dx, dy, dz |