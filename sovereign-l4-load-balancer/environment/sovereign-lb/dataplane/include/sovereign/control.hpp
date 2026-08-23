#pragma once
#include "sovereign/checkpoint.hpp"
#include "sovereign/drain.hpp"
#include "sovereign/protocol.hpp"
#include "sovereign/proxy.hpp"
#include "sovereign/status.hpp"
#include <atomic>
#include <string>
namespace sovereign {
struct NodeConfig {
	std::string node_id;
	std::string session_id;
	std::string zone;
	std::string control_host;
	std::uint16_t control_port{};
	std::string status_address;
	std::string state_root;
	std::uint32_t max_frame_bytes{4U << 20};
	std::size_t max_connections{10000};
};
NodeConfig load_node_config(const std::string& path);
class ControlClient {
 public:
	ControlClient(NodeConfig config, RuntimeStore& runtimes,
								CheckpointStore& checkpoints, Proxy& proxy,
								DrainManager& drains, Counters& counters)
			: config_(std::move(config)), runtimes_(runtimes), checkpoints_(checkpoints),
				proxy_(proxy), drains_(drains), counters_(counters) {}
	void run(std::atomic_bool& stopping);

 private:
	int connect_once() const;
	void session(int descriptor, std::atomic_bool& stopping);
	void handle(int descriptor, const Envelope& request);
	void send(int descriptor, const Envelope& envelope);
	Envelope reply(const std::string& type, const Envelope& request,
								 Json::Object body = {});
	NodeConfig config_;
	RuntimeStore& runtimes_;
	CheckpointStore& checkpoints_;
	Proxy& proxy_;
	DrainManager& drains_;
	Counters& counters_;
	std::uint64_t sequence_{1};
};
}