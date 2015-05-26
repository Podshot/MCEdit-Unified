#ifndef NO_ZLIB

#include "leveldb/zlib_compressor.h"

#include <zlib/zlib.h>
#include <algorithm>

namespace leveldb {

	void ZlibCompressor::compressImpl(const char* input, size_t length, ::std::string& buffer) const
	{
		const size_t BUFSIZE = 128 * 1024;
		unsigned char temp_buffer[BUFSIZE];

		//reserve enough memory to not reallocate on the fly
		buffer.reserve(compressBound(length));

		z_stream strm;
		strm.zalloc = 0;
		strm.zfree = 0;
		strm.next_in = (unsigned char *)(input);
		strm.avail_in = (uint32_t)length;
		strm.next_out = temp_buffer;
		strm.avail_out = BUFSIZE;

		deflateInit(&strm, compressionLevel);

		int deflate_res = Z_OK;
		while (strm.avail_in != 0)
		{
			int res = deflate(&strm, Z_NO_FLUSH);
			assert(res == Z_OK);
			if (strm.avail_out == 0)
			{
				buffer.insert(buffer.end(), temp_buffer, temp_buffer + BUFSIZE);
				strm.next_out = temp_buffer;
				strm.avail_out = BUFSIZE;
			}
		}

		while (deflate_res == Z_OK)
		{
			if (strm.avail_out == 0)
			{
				buffer.insert(buffer.end(), temp_buffer, temp_buffer + BUFSIZE);
				strm.next_out = temp_buffer;
				strm.avail_out = BUFSIZE;
			}
			deflate_res = deflate(&strm, Z_FINISH);
		}

		assert(deflate_res == Z_STREAM_END);
		buffer.insert(buffer.end(), temp_buffer, temp_buffer + BUFSIZE - strm.avail_out);
		deflateEnd(&strm);
	}

	int _zlibInflate(const char* input, size_t length, ::std::string &output) {
		const int CHUNK = 64 * 1024;

		int ret;
		size_t have;
		z_stream strm;
		unsigned char out[CHUNK];

		/* allocate inflate state */
		strm.zalloc = Z_NULL;
		strm.zfree = Z_NULL;
		strm.opaque = Z_NULL;
		strm.avail_in = (uint32_t)length;
		strm.next_in = (Bytef*)input;
		ret = inflateInit(&strm);
		if (ret != Z_OK)
			return ret;

		/* decompress until deflate stream ends or end of file */
		do {
			/* run inflate() on input until output buffer not full */
			do {

				strm.avail_out = CHUNK;
				strm.next_out = out;

				ret = inflate(&strm, Z_NO_FLUSH);
				assert(ret != Z_STREAM_ERROR);  /* state not clobbered */
				switch (ret) {
				case Z_NEED_DICT:
					ret = Z_DATA_ERROR;     /* and fall through */
				case Z_DATA_ERROR:
				case Z_MEM_ERROR:
					(void)inflateEnd(&strm);
					return ret;
				}

				have = CHUNK - strm.avail_out;

				output.append((char*)out, have);

			} while (strm.avail_out == 0);

			/* done when inflate() says it's done */
		} while (ret != Z_STREAM_END);

		/* clean up and return */
		(void)inflateEnd(&strm);
		return ret == Z_STREAM_END ? Z_OK : Z_DATA_ERROR;
	}

	bool ZlibCompressor::decompress(const char* input, size_t length, ::std::string &output) const {
		return _zlibInflate(input, length, output) == Z_OK;
	}
		
}

#endif