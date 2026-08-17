#pragma once

#include <cstddef>
#include <cstdint>

extern "C" {

void* sv_open(const char* data_dir, char* err, std::size_t err_len);
void sv_close(void* handle);
std::uint64_t sv_current_sequence(void* handle);
std::uint64_t sv_begin(void* handle, char* err, std::size_t err_len);
int sv_put(void* handle, std::uint64_t tx_id, const char* key_hex, const char* value_hex,
           char* err, std::size_t err_len);
int sv_del(void* handle, std::uint64_t tx_id, const char* key_hex,
           char* err, std::size_t err_len);
char* sv_get(void* handle, std::uint64_t tx_id, const char* key_hex, int* status,
             char* err, std::size_t err_len);
char* sv_scan(void* handle, std::uint64_t tx_id, const char* prefix_hex, int* status,
              char* err, std::size_t err_len);
int sv_commit(void* handle, std::uint64_t tx_id, std::uint64_t* commit_seq,
              char* err, std::size_t err_len);
int sv_rollback(void* handle, std::uint64_t tx_id, char* err, std::size_t err_len);
int sv_checkpoint(void* handle, std::uint64_t* checkpoint_seq,
                  char* err, std::size_t err_len);
char* sv_stats(void* handle, char* err, std::size_t err_len);
void sv_free_string(char* value);

}
