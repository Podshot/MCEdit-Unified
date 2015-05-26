// Copyright (c) 2011 The LevelDB Authors. All rights reserved.
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file. See the AUTHORS file for names of contributors.
#ifdef WIN32

#include <deque>

#include <windows.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <time.h>
#include <io.h>
#include "leveldb/env.h"
#include "leveldb/slice.h"

#include "util/win_logger.h"
#include "port/port.h"
#include "util/logging.h"


#include <fstream>
#include <algorithm>
#include <sstream>
#include <chrono>
#include <ctime>
#include <memory>
#include <condition_variable>
#include <thread>

namespace leveldb {
	namespace {

		// returns the ID of the current process
		static uint32_t current_process_id(void) {
			return static_cast<uint32_t>(::GetCurrentProcessId());
		}

		// returns the ID of the current thread
		static uint32_t current_thread_id(void) {
			return static_cast<uint32_t>(::GetCurrentThreadId());
		}

		static char global_read_only_buf[0x8000];

		class WinSequentialFile : public SequentialFile {
		private:
			std::string filename_;
			FILE* file_;

		public:
			WinSequentialFile(const std::string& fname, FILE* f)
				: filename_(fname), file_(f) {}
			virtual ~WinSequentialFile() { fclose(file_); }

			virtual Status Read(size_t n, Slice* result, char* scratch) {
				Status s;
				size_t r = fread_unlocked(scratch, 1, n, file_);
				*result = Slice(scratch, r);
				if(r < n) {
					if(feof(file_)) {
						// We leave status as ok if we hit the end of the file
					} else {
						// A partial read with an error: return a non-ok status
						s = Status::IOError(filename_, strerror(errno));
					}
			}
				return s;
		}

			virtual Status Skip(uint64_t n) {
				if(fseek(file_, n, SEEK_CUR)) {
					return Status::IOError(filename_, strerror(errno));
				}
				return Status::OK();
			}
		};

		class WinRandomAccessFile : public RandomAccessFile {
		private:
			std::string filename_;
			int fd_;
			mutable std::mutex mu_;

		public:
			WinRandomAccessFile(const std::string& fname, int fd)
				: filename_(fname), fd_(fd) {}
			virtual ~WinRandomAccessFile() { close(fd_); }

			virtual Status Read(uint64_t offset, size_t n, Slice* result,
				char* scratch) const {
				Status s;
				// no pread on Windows so we emulate it with a mutex
				std::unique_lock<std::mutex> lock(mu_);

				if(::_lseeki64(fd_, offset, SEEK_SET) == -1L) {
					return Status::IOError(filename_, strerror(errno));
				}

				int r = ::_read(fd_, scratch, n);
				*result = Slice(scratch, (r < 0) ? 0 : r);
				lock.unlock();
				if(r < 0) {
					// An error: return a non-ok status
					s = Status::IOError(filename_, strerror(errno));
				}
				return s;
			}
		};

		// We preallocate up to an extra megabyte and use memcpy to append new
		// data to the file.  This is safe since we either properly close the
		// file before reading from it, or for log files, the reading code
		// knows enough to skip zero suffixes.

		class WinFile : public WritableFile {

		public:
			explicit WinFile(std::string path) : path_(path), written_(0) {
				Open();
			}

			virtual ~WinFile() {
				Close();
			}

		private:
			void Open() {
				// we truncate the file as implemented in env_posix
				file_.open(path_.c_str(),
					std::ios_base::trunc | std::ios_base::out | std::ios_base::binary);
				written_ = 0;
			}

		public:
			virtual Status Append(const Slice& data) {
				Status result;
				file_.write(data.data(), data.size());
				if(!file_.good()) {
					result = Status::IOError(
						path_ + " Append", "cannot write");
				}
				return result;
			}

			virtual Status Close() {
				Status result;

				try {
					if(file_.is_open()) {
						Sync();
						file_.close();
					}
				} catch(const std::exception & e) {
					result = Status::IOError(path_ + " close", e.what());
				}

				return result;
			}

			virtual Status Flush() {
				file_.flush();
				return Status::OK();
			}

			virtual Status Sync() {
				Status result;
				try {
					Flush();
				} catch(const std::exception & e) {
					result = Status::IOError(path_ + " sync", e.what());
				}

				return result;
			}

		private:
			std::string path_;
			uint64_t written_;
			std::ofstream file_;
		};



		class WinFileLock : public FileLock {
		public:
			WinFileLock(const std::string& path) {
				fileHandle = CreateFileA(path.c_str(),
					GENERIC_READ | GENERIC_WRITE,
					FILE_SHARE_DELETE | FILE_SHARE_READ,
					NULL,
					OPEN_ALWAYS,
					FILE_ATTRIBUTE_NORMAL,
					NULL);
				fileSizeLow = GetFileSize(fileHandle, &fileSizeHigh);
				LockFile(fileHandle, 0, 0, fileSizeLow, fileSizeHigh);
			}
			~WinFileLock() {
				UnlockFile(fileHandle, 0, 0, fileSizeLow, fileSizeHigh);
				CloseHandle(fileHandle);
			}

		private:
			HANDLE fileHandle = 0;
			DWORD fileSizeHigh = 0;
			DWORD fileSizeLow = 0;
		};

		class WinEnv : public Env {
		public:
			WinEnv();
			virtual ~WinEnv() {
				fprintf(stderr, "Destroying Env::Default()\n");
			}

			virtual Status NewSequentialFile(const std::string& fname,
				SequentialFile** result) {
				FILE* f = fopen(fname.c_str(), "rb");
				if(f == NULL) {
					*result = NULL;
					return Status::IOError(fname, strerror(errno));
				} else {
					*result = new WinSequentialFile(fname, f);
					return Status::OK();
				}
			}

			virtual Status NewRandomAccessFile(const std::string& fname,
				RandomAccessFile** result) {
#ifdef WIN32
				int fd = _open(fname.c_str(), _O_RDONLY | _O_RANDOM | _O_BINARY);
#else
				int fd = open(fname.c_str(), O_RDONLY);
#endif
				if(fd < 0) {
					*result = NULL;
					return Status::IOError(fname, strerror(errno));
				}
				*result = new WinRandomAccessFile(fname, fd);
				return Status::OK();
			}

			virtual Status NewWritableFile(const std::string& fname,
				WritableFile** result) {
				Status s;
				try {
					// will create a new empty file to write to
					*result = new WinFile(fname);
				} catch(const std::exception & e) {
					s = Status::IOError(fname, e.what());
				}

				return s;
			}

			virtual bool FileExists(const std::string& fname) {
				DWORD attribs = GetFileAttributesA(fname.c_str());
				return attribs != INVALID_FILE_ATTRIBUTES;
			}
			Status getLastWindowsError(const std::string& name) {
				char lpBuffer[256] = "?";
				FormatMessageA(FORMAT_MESSAGE_FROM_SYSTEM,                 // It´s a system error
					NULL,                                      // No string to be formatted needed
					GetLastError(),                               // Hey Windows: Please explain this error!
					MAKELANGID(LANG_NEUTRAL, SUBLANG_DEFAULT),  // Do it in the standard language
					lpBuffer,              // Put the message here
					sizeof(lpBuffer) - 1,                     // Number of bytes to store the message
					NULL);
				return Status::IOError(name, lpBuffer);
			}
			virtual Status GetChildren(const std::string& dir,
				std::vector<std::string>* result) {
				std::string path = dir;
				result->clear();

				WIN32_FIND_DATA ffd;
				HANDLE hFind;
				path = dir + "/*";
				hFind = FindFirstFileA(path.c_str(), &ffd);

				if(INVALID_HANDLE_VALUE == hFind) {
					return getLastWindowsError(path);
				}

				do {
					result->push_back(ffd.cFileName);
				} while(FindNextFile(hFind, &ffd) != 0);

				return Status::OK();
			}

			virtual Status DeleteFile(const std::string& fname) {
				if(::DeleteFileA(fname.c_str()) != 0) {
					return Status::OK();
				} else {
					return getLastWindowsError(fname);
				}
			}

#define MAX_FILENAME 512
			virtual Status CreateDir(const std::string& name) {
				std::string path = name;
				std::replace(path.begin(), path.end(), '/', '\\');
				char tmpName[MAX_FILENAME];
				strcpy(tmpName, path.c_str());

				// Create parent directories
				for(LPTSTR p = strchr(tmpName, '\\'); p; p = strchr(p + 1, '\\')) {
					*p = 0;
					::CreateDirectoryA(tmpName, NULL);  // may or may not already exist
					*p = '\\';
				}

				::CreateDirectoryA(path.c_str(), NULL);
				return Status::OK();
			};

			virtual Status DeleteDir(const std::string& name) {
				int len = strlen(name.c_str());
				//TCHAR *pszFrom = new TCHAR[len+2];
				char* pszFrom = new char[len + 2];
				strcpy(pszFrom, name.c_str());
				pszFrom[len] = 0;
				pszFrom[len + 1] = 0;

				SHFILEOPSTRUCTA fileop;
				fileop.hwnd = NULL;    // no status display
				fileop.wFunc = FO_DELETE;  // delete operation
				fileop.pFrom = pszFrom;  // source file name as double null terminated string
				fileop.pTo = NULL;    // no destination needed
				fileop.fFlags = FOF_NOCONFIRMATION | FOF_SILENT;  // do not prompt the user

				fileop.fAnyOperationsAborted = FALSE;
				fileop.lpszProgressTitle = NULL;
				fileop.hNameMappings = NULL;

				int ret = SHFileOperationA(&fileop);
				delete[] pszFrom;
				if(ret != 0) {
					std::stringstream ss;
					ss << "Problem deleting directory: " << ret;
					Status::IOError(name, ss.str());
				}
				return Status::OK();
			};

			virtual Status GetFileSize(const std::string& fname, uint64_t* size) {
				HANDLE fileHandle = CreateFileA(fname.c_str(),
					GENERIC_READ | GENERIC_WRITE,
					FILE_SHARE_DELETE | FILE_SHARE_READ,
					NULL,
					OPEN_ALWAYS,
					FILE_ATTRIBUTE_NORMAL,
					NULL);
				if(fileHandle == 0) {
					return getLastWindowsError(fname);
				}
				DWORD fileSizeHigh = 0;
				DWORD fileSizeLow = ::GetFileSize(fileHandle, &fileSizeHigh);

				CloseHandle(fileHandle);
				if(fileSizeLow == 0) {
					return getLastWindowsError(fname);
				}

				return Status::OK();
			}

			virtual Status RenameFile(const std::string& src, const std::string& target) {
				DeleteFile(target);
				if(MoveFileA(src.c_str(), target.c_str()) != TRUE) {
					return getLastWindowsError(src);
				} else {
					return Status::OK();
				}
			}

			virtual Status LockFile(const std::string& fname, FileLock** lock) {
				*lock = NULL;

				Status status;
				if(!FileExists(fname)) {
					std::ofstream of(fname, std::ios_base::trunc | std::ios_base::out);
				}
				*lock = new WinFileLock(fname);

				return Status::OK();
			}

			virtual Status UnlockFile(FileLock* lock) {
				delete lock;
				return Status::OK();
			}

			virtual void Schedule(void(*function)(void*), void* arg);

			virtual void StartThread(void(*function)(void* arg), void* arg);

			virtual Status GetTestDirectory(std::string* result) {
				std::stringstream ss;
				ss << "tmp/leveldb_tests/" << current_process_id();

				// Directory may already exist
				CreateDir(ss.str());

				*result = ss.str();

				return Status::OK();
			}

#ifndef WIN32
			static uint64_t gettid() {
				pthread_t tid = pthread_self();
				uint64_t thread_id = 0;
				memcpy(&thread_id, &tid, std::min(sizeof(thread_id), sizeof(tid)));
				return thread_id;
			}
#endif

			virtual Status NewLogger(const std::string& fname, Logger** result) {
				FILE* f = fopen(fname.c_str(), "wt");
				if(f == NULL) {
					*result = NULL;
					return Status::IOError(fname, strerror(errno));
				} else {
#ifdef WIN32
					*result = new WinLogger(f);
#else
					*result = new PosixLogger(f, &WinEnv::gettid);
#endif
					return Status::OK();
				}
			}

			struct timezone {
				int  tz_minuteswest; /* minutes W of Greenwich */
				int  tz_dsttime;     /* type of dst correction */
			};
#if defined(_MSC_VER) || defined(_MSC_EXTENSIONS)
#define DELTA_EPOCH_IN_MICROSECS  116444736000000000Ui64 // CORRECT
#else
#define DELTA_EPOCH_IN_MICROSECS  116444736000000000ULL // CORRECT
#endif
			int gettimeofday(struct timeval *tv, struct timezone *tz) {
				FILETIME ft;
				uint64_t tmpres = 0;
				static int tzflag = 0;

				if(tv) {
					GetSystemTimeAsFileTime(&ft);
					tmpres |= ft.dwHighDateTime;
					tmpres <<= 32;
					tmpres |= ft.dwLowDateTime;

					/*converting file time to unix epoch*/
					tmpres /= 10;  /*convert into microseconds*/
					tmpres -= DELTA_EPOCH_IN_MICROSECS;
					tv->tv_sec = (long)(tmpres / 1000000UL);
					tv->tv_usec = (long)(tmpres % 1000000UL);
				}

				if(tz) {
					if(!tzflag) {
						_tzset();
						tzflag++;
					}
					tz->tz_minuteswest = _timezone / 60;
					tz->tz_dsttime = _daylight;
				}

				return 0;
			}

			virtual uint64_t NowMicros() {
				struct timeval tv;
				gettimeofday(&tv, 0);
				return static_cast<uint64_t>(tv.tv_sec) * 1000000 + tv.tv_usec;
			}

			virtual void SleepForMicroseconds(int micros) {
				std::this_thread::sleep_for(std::chrono::microseconds(micros));
			}


		private:
			void PthreadCall(const char* label, int result) {
				if(result != 0) {
					fprintf(stderr, "pthread %s: %s\n", label, strerror(result));
					exit(1);
				}
			}

			// BGThread() is the body of the background thread
			void BGThread();

			static void* BGThreadWrapper(void* arg) {
				reinterpret_cast<WinEnv*>(arg)->BGThread();
				return NULL;
			}

			std::mutex mu_;
			std::condition_variable bgsignal_;
			std::unique_ptr<std::thread> bgthread_;

			// Entry per Schedule() call
			struct BGItem { void* arg; void(*function)(void*); };
			typedef std::deque<BGItem> BGQueue;
			BGQueue queue_;
		};

		WinEnv::WinEnv() {}

		void WinEnv::Schedule(void(*function)(void*), void* arg) {
			std::unique_lock<std::mutex> lock(mu_);

			// Start background thread if necessary
			if(!bgthread_) {
				bgthread_.reset(
					new std::thread(&WinEnv::BGThreadWrapper, this));
			}

			// Add to priority queue
			queue_.push_back(BGItem());
			queue_.back().function = function;
			queue_.back().arg = arg;

			lock.unlock();

			bgsignal_.notify_one();

		}

		void WinEnv::BGThread() {
			while(true) {
				// Wait until there is an item that is ready to run
				std::unique_lock<std::mutex> lock(mu_);

				while(queue_.empty()) {
					bgsignal_.wait(lock);
				}

				void(*function)(void*) = queue_.front().function;
				void* arg = queue_.front().arg;
				queue_.pop_front();

				lock.unlock();
				(*function)(arg);
			}
		}

		namespace {
			struct StartThreadState {
				void(*user_function)(void*);
				void* arg;
			};
		}

		DWORD WINAPI StartThreadWrapper(LPVOID lpParam) {
 			StartThreadState* state = reinterpret_cast<StartThreadState*>(lpParam);
 			state->user_function(state->arg);
 			delete state;
 			return 0;
 		}
 
		void WinEnv::StartThread(void(*function)(void* arg), void* arg) {
 			StartThreadState* state = new StartThreadState;
 			state->user_function = function;
 			state->arg = arg;
			DWORD     thread_id;
 			CreateThread(
 				NULL,                   // default security attributes
 				0,                      // use default stack size  
				StartThreadWrapper,       // thread function name
 				state,          // argument to thread function 
 				0,                      // use default creation flags 
				&thread_id);   // returns the thread identifier 
 		}

		//void WinEnv::StartThread(void(*function)(void* arg), void* arg) {
		//	StartThreadState* state = new StartThreadState;
		//	state->user_function = function;
		//	state->arg = arg;

		//	boost::thread t(boost::bind(&StartThreadWrapper, state));
		//}
	}

	static INIT_ONCE g_InitOnce = INIT_ONCE_STATIC_INIT;
	static Env* default_env;
	static BOOL CALLBACK InitDefaultEnv(PINIT_ONCE InitOnce,
		PVOID Parameter,
		PVOID *lpContext) {
		::memset(global_read_only_buf, 0, sizeof(global_read_only_buf));
		default_env = new WinEnv;
		return TRUE;
	}

	Env* Env::Default() {
		PVOID lpContext;
		InitOnceExecuteOnce(&g_InitOnce,          // One-time initialization structure
			InitDefaultEnv,   // Pointer to initialization callback function
			NULL,                 // Optional parameter to callback function (not used)
			&lpContext);          // Receives pointer to event object stored in g_InitOnce

		return default_env;
	}

}

#endif