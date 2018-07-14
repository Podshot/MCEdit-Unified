from pymclevel.materials import BlockstateAPI
from pymclevel import nbt
import numpy

def perform(level, box, options):
    block_api = level.materials.blockstate_api
    assert isinstance(block_api, BlockstateAPI)
    print block_api.idToBlockstate(251, 1)

    root = nbt.TAG_Compound()
    data = nbt.TAG_Compound()
    iarray = nbt.TAG_Int_Array()
    data['test1'] = iarray

    #array = nbt.TAG_Long_Array()
    #root['test'] = array
    root['data'] = data


    print root
    root.save('test.nbt')


