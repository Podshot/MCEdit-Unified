
#pragma once

#include "leveldb/compressor.h"

namespace leveldb {

	class DLLX ZlibCompressor : public Compressor 
	{
	public:
		static const int SERIALIZE_ID = 2;

		const int compressionLevel;
        
        virtual ~ZlibCompressor() {
            
        }

		ZlibCompressor(int compressionLevel = -1) :
			Compressor(SERIALIZE_ID),
			compressionLevel(compressionLevel)
		{
			assert(compressionLevel >= -1 && compressionLevel <= 9);
		}

		virtual void compressImpl(const char* input, size_t length, ::std::string& output) const override;

		virtual bool decompress(const char* input, size_t length, ::std::string &output) const override;

	private:

	};
}