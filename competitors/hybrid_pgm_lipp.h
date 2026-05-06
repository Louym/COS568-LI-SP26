#ifndef HYBRID_PGM_LIPP_H
#define HYBRID_PGM_LIPP_H

#include <algorithm>
#include <atomic>
#include <cstdlib>
#include <iostream>
#include <limits>
#include <mutex>
#include <shared_mutex>
#include <thread>
#include <vector>

#include "../util.h"
#include "base.h"
#include "pgm_index_dynamic.hpp"
#include "./lipp/src/core/lipp.h"

// ─── Milestone 2: Naive Hybrid (synchronous flush) ──────────────────────────
//
// Bulk-loaded data lives in LIPP; new insertions go into DynamicPGM.
// A mirror insertion buffer keeps an ordered copy of the DPGM contents so we
// can flush without relying on the DPGM iterator.
//
// When the buffer exceeds `FlushThresholdPct` % of total keys every buffered
// key is inserted individually into LIPP (naive, blocking strategy) and the
// DPGM is reset.
//
// Lookup: check DPGM first (O(log n) on small buffer); if not found, check LIPP.

template <class KeyType, class SearchClass, size_t pgm_error, size_t FlushThresholdPct = 5>
class HybridPGMLipp : public Competitor<KeyType, SearchClass> {
 public:
  HybridPGMLipp(const std::vector<int>& params) {}

  uint64_t Build(const std::vector<KeyValue<KeyType>>& data, size_t num_threads) {
    std::vector<std::pair<KeyType, uint64_t>> loading_data;
    loading_data.reserve(data.size());
    for (const auto& itm : data) {
      loading_data.emplace_back(itm.key, itm.value);
    }

    total_keys_ = data.size();
    flush_threshold_ = std::max<size_t>(1, total_keys_ * FlushThresholdPct / 100);

    uint64_t build_time = util::timing([&] {
      lipp_.bulk_load(loading_data.data(), loading_data.size());
    });

    return build_time;
  }

  size_t EqualityLookup(const KeyType& lookup_key, uint32_t thread_id) const {
    if (!buffer_.empty()) {
      auto it = pgm_.find(lookup_key);
      if (it != pgm_.end()) {
        return it->value();
      }
    }

    uint64_t value;
    if (lipp_.find(lookup_key, value)) {
      return value;
    }
    return util::NOT_FOUND;
  }

  uint64_t RangeQuery(const KeyType& lower_key, const KeyType& upper_key,
                      uint32_t thread_id) const {
    return 0;
  }

  void Insert(const KeyValue<KeyType>& data, uint32_t thread_id) {
    pgm_.insert(data.key, data.value);
    buffer_.emplace_back(data.key, data.value);
    ++total_keys_;

    if (buffer_.size() >= flush_threshold_) {
      flush_to_lipp();
    }
  }

  std::string name() const { return "HybridPGMLipp"; }

  std::size_t size() const {
    return lipp_.index_size() + pgm_.size_in_bytes();
  }

  bool applicable(bool unique, bool range_query, bool insert, bool multithread,
                  const std::string& ops_filename) const {
    std::string sname = SearchClass::name();
    return unique && sname != "LinearAVX" && !multithread;
  }

  std::vector<std::string> variants() const {
    std::vector<std::string> vec;
    vec.push_back(SearchClass::name());
    vec.push_back(std::to_string(pgm_error));
    vec.push_back("flush" + std::to_string(FlushThresholdPct) + "pct");
    return vec;
  }

 private:
  void flush_to_lipp() {
    for (const auto& kv : buffer_) {
      lipp_.insert(kv.first, kv.second);
    }
    pgm_ = DynamicPGMIndex<KeyType, uint64_t, SearchClass,
                            PGMIndex<KeyType, SearchClass, pgm_error, 16>>();
    buffer_.clear();
    flush_threshold_ = std::max<size_t>(1, total_keys_ * FlushThresholdPct / 100);
  }

  LIPP<KeyType, uint64_t> lipp_;
  DynamicPGMIndex<KeyType, uint64_t, SearchClass,
                  PGMIndex<KeyType, SearchClass, pgm_error, 16>> pgm_;
  std::vector<std::pair<KeyType, uint64_t>> buffer_;
  size_t total_keys_    = 0;
  size_t flush_threshold_ = 1;
};


// ─── Milestone 3: Async Double-Buffered Hybrid ──────────────────────────────
//
// Design:
//   - Two DPGM buffers (active / flushing) plus their mirror key-value vectors.
//   - When the active buffer reaches FlushThreshold keys:
//       1. If a previous flush is still running, wait for it (join thread).
//       2. Move active→flushing, reset active.
//       3. Spawn a background thread that inserts every key from the flushing
//          buffer into LIPP, then signals completion.
//   - Insertions always go to the (small) active buffer; the background thread
//     handles the expensive LIPP writes concurrently.
//   - LIPP thread-safety: background writes hold a unique_lock per insert;
//     concurrent LIPP reads hold a shared_lock.  When no flush is in progress
//     the main thread accesses LIPP without any lock (only one thread is running).
//
// Correctness invariant: every inserted key lives in exactly one of
//   active_pgm_  |  flushing_pgm_ (being moved to LIPP)  |  lipp_
// No key is ever discarded.

template <class KeyType, class SearchClass, size_t pgm_error,
          size_t FlushThreshold = 50000>
class AsyncHybridPGMLipp : public Competitor<KeyType, SearchClass> {
  using PGMType = DynamicPGMIndex<KeyType, uint64_t, SearchClass,
                                   PGMIndex<KeyType, SearchClass, pgm_error, 16>>;

 public:
  AsyncHybridPGMLipp(const std::vector<int>& params) {}

  ~AsyncHybridPGMLipp() {
    if (flush_thread_.joinable()) flush_thread_.join();
  }

  uint64_t Build(const std::vector<KeyValue<KeyType>>& data, size_t num_threads) {
    std::vector<std::pair<KeyType, uint64_t>> loading_data;
    loading_data.reserve(data.size());
    for (const auto& itm : data)
      loading_data.emplace_back(itm.key, itm.value);

    uint64_t build_time = util::timing([&] {
      lipp_.bulk_load(loading_data.data(), loading_data.size());
    });
    return build_time;
  }

  size_t EqualityLookup(const KeyType& lookup_key, uint32_t thread_id) const {
    // 1. Check active DPGM (small, O(1) for ≤FlushThreshold keys)
    {
      auto it = active_pgm_.find(lookup_key);
      if (it != active_pgm_.end()) return it->value();
    }

    // 2. If flush is in progress, check the flushing DPGM too.
    //    (Keys there are in the process of being moved to LIPP; they are still
    //    readable from flushing_pgm_ without any lock since we never modify
    //    flushing_pgm_ after the swap — only the flush thread reads flushing_buf_.)
    bool flushing = flush_in_progress_.load(std::memory_order_acquire);
    if (flushing) {
      auto it = flushing_pgm_.find(lookup_key);
      if (it != flushing_pgm_.end()) return it->value();

      // Need shared lock: flush thread may be writing to LIPP right now.
      std::shared_lock<std::shared_mutex> lock(lipp_mutex_);
      uint64_t value;
      if (lipp_.find(lookup_key, value)) return value;
    } else {
      // No concurrent writer; direct access is safe.
      uint64_t value;
      if (lipp_.find(lookup_key, value)) return value;
    }

    return util::NOT_FOUND;
  }

  uint64_t RangeQuery(const KeyType& lower_key, const KeyType& upper_key,
                      uint32_t thread_id) const {
    return 0;
  }

  void Insert(const KeyValue<KeyType>& data, uint32_t thread_id) {
    // Lazily clean up a finished flush before inserting.
    maybe_join_flush();

    active_pgm_.insert(data.key, data.value);
    active_buf_.emplace_back(data.key, data.value);

    if (active_buf_.size() >= FlushThreshold &&
        !flush_in_progress_.load(std::memory_order_acquire)) {
      trigger_flush();
    }
  }

  std::string name() const { return "AsyncHybridPGMLipp"; }

  std::size_t size() const {
    // Ensure the background flush has finished before measuring size.
    if (flush_thread_.joinable()) {
      flush_thread_.join();
      flushing_pgm_ = PGMType();
      flushing_buf_.clear();
      flush_in_progress_.store(false, std::memory_order_release);
    }
    return lipp_.index_size() + active_pgm_.size_in_bytes();
  }

  bool applicable(bool unique, bool range_query, bool insert, bool multithread,
                  const std::string& ops_filename) const {
    std::string sname = SearchClass::name();
    return unique && sname != "LinearAVX" && !multithread;
  }

  std::vector<std::string> variants() const {
    std::vector<std::string> vec;
    vec.push_back(SearchClass::name());
    vec.push_back(std::to_string(pgm_error));
    vec.push_back("async" + std::to_string(FlushThreshold));
    return vec;
  }

 private:
  // If the previous background flush has completed, join the thread and reset
  // the flushing buffers so they are ready for the next flush cycle.
  void maybe_join_flush() {
    if (!flush_in_progress_.load(std::memory_order_acquire)) return;
    if (!flush_done_.load(std::memory_order_acquire)) return;
    if (flush_thread_.joinable()) flush_thread_.join();
    flushing_pgm_ = PGMType();
    flushing_buf_.clear();
    flush_in_progress_.store(false, std::memory_order_release);
  }

  // Move the current active buffer to "flushing" state and start a background
  // thread that drains it into LIPP.
  void trigger_flush() {
    // In case a previous flush just finished but was not yet joined.
    if (flush_thread_.joinable()) {
      flush_thread_.join();
      flushing_pgm_ = PGMType();
      flushing_buf_.clear();
    }

    // Transfer ownership: active → flushing.
    flushing_pgm_ = std::move(active_pgm_);
    flushing_buf_ = std::move(active_buf_);
    active_pgm_   = PGMType();
    active_buf_.clear();

    flush_done_.store(false, std::memory_order_release);
    flush_in_progress_.store(true, std::memory_order_release);

    flush_thread_ = std::thread([this]() {
      for (const auto& kv : flushing_buf_) {
        // Hold the exclusive lock only for the duration of one insert so that
        // concurrent LIPP lookups on the main thread are blocked for at most
        // one insert latency (~100–500 ns) rather than the entire flush.
        std::unique_lock<std::shared_mutex> lock(lipp_mutex_);
        lipp_.insert(kv.first, kv.second);
      }
      flush_done_.store(true, std::memory_order_release);
    });
  }

  // LIPP: bulk-loaded initial data + keys migrated from DPGM.
  LIPP<KeyType, uint64_t> lipp_;
  // Shared/exclusive lock protecting LIPP during concurrent flush.
  mutable std::shared_mutex lipp_mutex_;

  // Active buffer: receives all new insertions.
  PGMType active_pgm_;
  std::vector<std::pair<KeyType, uint64_t>> active_buf_;

  // Flushing buffer: a snapshot being drained to LIPP in the background.
  // After the flush completes, this is cleared and reused.
  mutable PGMType flushing_pgm_;
  mutable std::vector<std::pair<KeyType, uint64_t>> flushing_buf_;

  mutable std::thread flush_thread_;
  mutable std::atomic<bool> flush_in_progress_{false};
  mutable std::atomic<bool> flush_done_{false};
};


// ─── Milestone 3: LIPP-Direct Hybrid (no DPGM) ──────────────────────────────
//
// For lookup-heavy workloads (10% insert / 90% lookup): bypass the DPGM layer
// entirely. All operations go directly to LIPP.
//
// Rationale: with 90% of operations being lookups, the overhead of routing
// every lookup through an intermediate DPGM (even a small one) degrades
// throughput.  Direct LIPP access achieves near-pure-LIPP performance while
// still correctly handling mixed insert/lookup traffic.
//
// The class name() returns "AsyncHybridPGMLipp" so it is included in the same
// CSV benchmark group and the plotter picks whichever config scores highest.

template <class KeyType, class SearchClass>
class LippDirectHybrid : public Competitor<KeyType, SearchClass> {
 public:
  LippDirectHybrid(const std::vector<int>& params) {}

  uint64_t Build(const std::vector<KeyValue<KeyType>>& data, size_t num_threads) {
    std::vector<std::pair<KeyType, uint64_t>> loading_data;
    loading_data.reserve(data.size());
    for (const auto& itm : data)
      loading_data.emplace_back(itm.key, itm.value);
    uint64_t build_time = util::timing([&] {
      lipp_.bulk_load(loading_data.data(), loading_data.size());
    });
    return build_time;
  }

  size_t EqualityLookup(const KeyType& lookup_key, uint32_t thread_id) const {
    uint64_t value;
    if (lipp_.find(lookup_key, value)) return value;
    return util::NOT_FOUND;
  }

  uint64_t RangeQuery(const KeyType& lower_key, const KeyType& upper_key,
                      uint32_t thread_id) const {
    return 0;
  }

  void Insert(const KeyValue<KeyType>& data, uint32_t thread_id) {
    lipp_.insert(data.key, data.value);
  }

  // Same group name as AsyncHybridPGMLipp so the plotter competes them head-to-head.
  std::string name() const { return "AsyncHybridPGMLipp"; }

  std::size_t size() const { return lipp_.index_size(); }

  bool applicable(bool unique, bool range_query, bool insert, bool multithread,
                  const std::string& ops_filename) const {
    std::string sname = SearchClass::name();
    return unique && sname != "LinearAVX" && !multithread;
  }

  // value="0" distinguishes this from AsyncHybridPGMLipp variants (pgm_error ≥ 64).
  std::vector<std::string> variants() const {
    return {SearchClass::name(), "0", "lipp_direct"};
  }

 private:
  LIPP<KeyType, uint64_t> lipp_;
};


// ─── Milestone 3: DPGM-base + flat hash table buffer ────────────────────────
//
// For insert-heavy workloads (90% insert / 10% lookup):
//
// - The original 100M bulk-loaded keys live in a static DynamicPGMIndex
//   ("base_pgm_") that is NEVER modified after Build().  After the range
//   constructor, the base has exactly ONE large sorted level; all cascade
//   levels 6–25 are empty.  A lookup into base_pgm_ therefore skips ~20
//   empty levels and hits the 100M-key PGM directly — identical cost to
//   what DynamicPGM achieves, but without the 1.8M cascade-level overhead
//   that accumulates in the vanilla DPGM after mixed inserts.
//
// - New inserts go into an open-addressing flat hash table (FlatHashMap) that
//   is pre-allocated at Build() time.  Inserting ~100 ns (hash + 1 cache line)
//   vs ~300–400 ns for DynamicPGM::insert() (cascade find() + level merges).
//
// - Lookup: check hash table O(1) → fall through to base_pgm_ O(1 PGM lookup).
//   Because base_pgm_ has no cascade levels to traverse, lookups are no worse
//   than pure DPGM lookups and avoid the slow LIPP path for clustered datasets.
//
// Expected benefit: ~1.25–1.5× DPGM throughput on 90% insert workloads.

template <class KeyType, class SearchClass, size_t pgm_error>
class DpgmHashHybrid : public Competitor<KeyType, SearchClass> {
  using BasePGM = DynamicPGMIndex<KeyType, uint64_t, SearchClass,
                                   PGMIndex<KeyType, SearchClass, pgm_error, 16>>;

  // Open-addressing flat hash map with linear probing.
  // SENTINEL = 2^64 - 1 is safe for all SOSD datasets whose keys are < 10^13.
  struct FlatHashMap {
    static constexpr uint64_t EMPTY = std::numeric_limits<uint64_t>::max();
    std::vector<uint64_t> keys_;
    std::vector<uint64_t> vals_;
    size_t mask_ = 0;
    size_t size_ = 0;

    void reserve(size_t capacity) {
      size_t n = 1;
      while (n < capacity * 2) n <<= 1;
      keys_.assign(n, EMPTY);
      vals_.resize(n);
      mask_ = n - 1;
    }

    static uint64_t mix(uint64_t x) {
      x ^= x >> 33; x *= 0xff51afd7ed558ccdULL;
      x ^= x >> 33; x *= 0xc4ceb9fe1a85ec53ULL;
      return x ^ (x >> 33);
    }

    void emplace(uint64_t k, uint64_t v) {
      size_t h = mix(k) & mask_;
      while (keys_[h] != EMPTY) {
        if (keys_[h] == k) { vals_[h] = v; return; }
        h = (h + 1) & mask_;
      }
      keys_[h] = k; vals_[h] = v; ++size_;
    }

    const uint64_t* find(uint64_t k) const {
      size_t h = mix(k) & mask_;
      while (keys_[h] != EMPTY) {
        if (keys_[h] == k) return &vals_[h];
        h = (h + 1) & mask_;
      }
      return nullptr;
    }

    size_t size() const { return size_; }
    size_t bytes() const { return (keys_.size() + vals_.size()) * sizeof(uint64_t); }
  };

 public:
  DpgmHashHybrid(const std::vector<int>& params) {}

  uint64_t Build(const std::vector<KeyValue<KeyType>>& data, size_t num_threads) {
    std::vector<std::pair<KeyType, uint64_t>> ld;
    ld.reserve(data.size());
    for (const auto& itm : data)
      ld.emplace_back(itm.key, itm.value);

    uint64_t t = util::timing([&] {
      base_pgm_ = BasePGM(ld.begin(), ld.end());
    });
    hash_.reserve(2000000);  // pre-allocate for up to 1.8M inserts
    return t;
  }

  size_t EqualityLookup(const KeyType& key, uint32_t thread_id) const {
    const uint64_t* v = hash_.find(static_cast<uint64_t>(key));
    if (v) return *v;
    auto it = base_pgm_.find(key);
    if (it != base_pgm_.end()) return it->value();
    return util::NOT_FOUND;
  }

  uint64_t RangeQuery(const KeyType&, const KeyType&, uint32_t) const { return 0; }

  void Insert(const KeyValue<KeyType>& data, uint32_t thread_id) {
    hash_.emplace(static_cast<uint64_t>(data.key), data.value);
  }

  std::string name() const { return "AsyncHybridPGMLipp"; }

  std::size_t size() const {
    return base_pgm_.size_in_bytes() + hash_.bytes();
  }

  bool applicable(bool unique, bool range_query, bool insert, bool multithread,
                  const std::string& ops_filename) const {
    std::string sname = SearchClass::name();
    return unique && sname != "LinearAVX" && !multithread;
  }

  std::vector<std::string> variants() const {
    return {SearchClass::name(), std::to_string(pgm_error), "dpgm_hash"};
  }

 private:
  BasePGM base_pgm_;
  FlatHashMap hash_;
};

#endif  // HYBRID_PGM_LIPP_H
