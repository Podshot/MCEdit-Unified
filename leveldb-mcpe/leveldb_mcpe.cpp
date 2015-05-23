//Rubisks trying to wrap leveldb-mcpe
#include <leveldb/db.h>
#define BOOST_PYTHON_STATIC_LIB
#include <boost/python/module.hpp>
#include <boost/python/def.hpp>
#include <boost/system/config.hpp>
#include <boost/python.hpp>
#include <stdint.h>
#include <stdio.h>

struct DBWrap : leveldb::DB, boost::python::wrapper<leveldb::DB>
{
public:
	leveldb::DB * _db;

	DBWrap(PyObject* _options, PyObject* _name) //Open(options, name, db)
	{
		const leveldb::Options options = boost::python::extract<const leveldb::Options&>(_options);
		std::string name = boost::python::extract<std::string>(_name);
		leveldb::Status s = leveldb::DB::Open(options, name, &_db);
	}


	leveldb::Status Put(const leveldb::WriteOptions& options,
		const leveldb::Slice& key,
		const leveldb::Slice& value)
	{
		return this->_db->Put(options, key, value);
	}

	leveldb::Status Delete(const leveldb::WriteOptions& options,
		const leveldb::Slice& key)
	{
		return this->_db->Delete(options, key);
	}

	leveldb::Status Write(const leveldb::WriteOptions& options,
		leveldb::WriteBatch* updates)
	{
		return this->_db->Write(options, updates);
	}

	leveldb::Status Get(const leveldb::ReadOptions& options,
		const leveldb::Slice& key,
		std::string* value)
	{
		return this->_db->Get(options, key, value);
	}

	leveldb::Iterator* NewIterator(const leveldb::ReadOptions& options)
	{
		return this->_db->NewIterator(options);
	}

	const leveldb::Snapshot* GetSnapshot()
	{
		return this->_db->GetSnapshot();
	}

	void GetApproximateSizes(const leveldb::Range* range, int n, uint64_t* sizes)
	{
		this->_db->GetApproximateSizes(range, n, sizes);
	}


	void ReleaseSnapshot(const leveldb::Snapshot* snapshot)
	{
		this->_db->ReleaseSnapshot(snapshot);
	}

	bool GetProperty(const leveldb::Slice& property, std::string* value)
	{
		return this->_db->GetProperty(property, value);
	}

	void CompactRange(const leveldb::Slice* begin, const leveldb::Slice* end)
	{
		this->_db->CompactRange(begin, end);
	}
};

BOOST_PYTHON_MODULE(leveldb_mcpe)
{
	//leveldb/db.h
	boost::python::class_<DBWrap, boost::noncopyable>("DB", boost::python::init<PyObject*, PyObject*>())
		.def("Put", &DBWrap::Put)
		.def("Delete", &DBWrap::Delete)
		.def("Write", &DBWrap::Write)
		.def("Get", &DBWrap::Get)
		.def("NewIterator", &DBWrap::NewIterator,
		boost::python::return_value_policy<boost::python::reference_existing_object>())
		.def("GetSnapshot", &DBWrap::GetSnapshot,
		boost::python::return_value_policy<boost::python::reference_existing_object>())
		.def("ReleaseSnapshot", &DBWrap::ReleaseSnapshot)
		.def("GetProperty", &DBWrap::GetProperty)
		.def("GetApproximateSizes", &DBWrap::GetApproximateSizes)
		.def("CompactRange", &DBWrap::CompactRange)
		;


	//leveldb/options.h
	boost::python::class_<leveldb::Options>("Options", boost::python::init<>())
		.def_readonly("comparator", &leveldb::Options::comparator)
		.def_readwrite("create_if_missing", &leveldb::Options::create_if_missing)
		.def_readwrite("error_if_exists", &leveldb::Options::error_if_exists)
		.def_readwrite("env", &leveldb::Options::env)
		.def_readwrite("info_log", &leveldb::Options::info_log)
		.def_readwrite("write_buffer_size", &leveldb::Options::write_buffer_size)
		.def_readwrite("max_open_files", &leveldb::Options::max_open_files)
		.def_readwrite("block_cache", &leveldb::Options::block_cache)
		.def_readwrite("block_size", &leveldb::Options::block_size)
		.def_readwrite("block_restart_interval", &leveldb::Options::block_restart_interval)
		//TODO setup a way to include compressor array
		.def_readonly("filter_policy", &leveldb::Options::filter_policy)
		;
}