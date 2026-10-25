#pragma once

#include "rs485_interface.h"
#include "esphome/components/uart/uart.h"
#include "esphome/core/gpio.h"
#include "esp_timer.h"
#include "driver/gpio.h"

namespace esphome::comfortzone {

class EspHomeRS485Interface: public RS485Interface {
public:
    EspHomeRS485Interface(uart::UARTDevice* uart_device, GPIOPin* re_de_pin, int rx_idle_pin = -1):
        uart_device_(uart_device),
        re_de_pin_(re_de_pin), rx_idle_pin_(rx_idle_pin) {}

    void begin() {
        re_de_pin_->pin_mode(gpio::FLAG_OUTPUT);
        enable_receiver_mode();
        if (rx_idle_pin_ >= 0) {
            const auto installed = gpio_install_isr_service(ESP_INTR_FLAG_IRAM);
            if (installed != ESP_OK && installed != ESP_ERR_INVALID_STATE) return;
            last_rx_edge_us_ = static_cast<uint32_t>(esp_timer_get_time());
            const auto pin = static_cast<gpio_num_t>(rx_idle_pin_);
            if (gpio_set_intr_type(pin, GPIO_INTR_ANYEDGE) != ESP_OK) return;
            edge_detection_ready_ = gpio_isr_handler_add(pin, rx_edge_, this) == ESP_OK;
        }
    }

    bool idle_break(uint32_t quiet_ms) override {
        if (!edge_detection_ready_ || gpio_get_level(static_cast<gpio_num_t>(rx_idle_pin_)) != 0) return false;
        const uint32_t last_edge = last_rx_edge_us_;
        return static_cast<uint32_t>(esp_timer_get_time()) - last_edge >= quiet_ms * 1000;
    }
    bool edge_detection_ready() const { return edge_detection_ready_; }

    bool observe_tx(int pin) {
        if (pin < 0 || (tx_monitor_pin_ >= 0 && tx_monitor_pin_ != pin)) return false;
        const auto p = static_cast<gpio_num_t>(pin);
        const auto installed = gpio_install_isr_service(ESP_INTR_FLAG_IRAM);
        if (installed != ESP_OK && installed != ESP_ERR_INVALID_STATE) return false;
        // Enable pad readback without replacing the UART output matrix route.
        if (gpio_input_enable(p) != ESP_OK || gpio_set_intr_type(p, GPIO_INTR_ANYEDGE) != ESP_OK ||
            gpio_isr_handler_add(p, tx_edge_, this) != ESP_OK) return false;
        tx_monitor_pin_ = pin;
        return true;
    }
    uint32_t tx_edges() const { return tx_edges_; }

    int available() {
        return uart_device_->available();
    }

    int read_byte() {
        const int value = uart_device_->read();
        if (value >= 0) ++rx_byte_count_;
        record_(value);
        return value;
    }
    uint32_t rx_byte_count() const { return rx_byte_count_; }

    int write_bytes(const void* data, int size) {
        for (int i = 0; i < size; ++i) record_(0x100 + static_cast<const uint8_t *>(data)[i]);
        uart_device_->write_array((const uint8_t*)data, size);
        return size;
    }

    void flush() {
        uart_device_->flush();
        record_(0x202);
        // Capture RO while DE/RE is still high, before re-enabling reception.
        sample_rx_pin();
    }

    void enable_receiver_mode() {
	    re_de_pin_->digital_write(false);
        record_(0x201);
    }

    void enable_sender_mode() {
	    re_de_pin_->digital_write(true);
        record_(0x200);
    }

    // Optional bounded trace. Timestamp is when software reads the byte, not
    // its electrical arrival. No network or logging calls occur in read_byte().
    void set_trace(bool enabled) {
        trace_enabled_ = enabled;
        trace_count_ = trace_sequence_ = trace_dropped_ = 0;
    }
    size_t trace_size() const { return trace_count_ ? 12 + trace_count_ * 6 : 0; }
    const uint8_t *trace_data() {
        trace_[0]='C'; trace_[1]='Z'; trace_[2]='R'; trace_[3]='X';
        put32_(trace_+4, trace_sequence_++);
        put32_(trace_+8, trace_dropped_);
        return trace_;
    }
    void clear_trace() { trace_count_ = 0; }
    void set_trace_rx_pin(int pin) { trace_rx_pin_ = pin; }
    void sample_rx_pin() {
        if (!trace_enabled_ || trace_rx_pin_ < 0) return;
        const uint32_t now = static_cast<uint32_t>(esp_timer_get_time());
        if (now - last_pin_sample_ < 1000) return;
        last_pin_sample_ = now;
        record_(0x300 + gpio_get_level(static_cast<gpio_num_t>(trace_rx_pin_)));
    }

private:
    static void IRAM_ATTR tx_edge_(void *arg) {
        auto *self = static_cast<EspHomeRS485Interface *>(arg);
        self->tx_edges_ = self->tx_edges_ + 1;
    }
    static void IRAM_ATTR rx_edge_(void *arg) {
        auto *self = static_cast<EspHomeRS485Interface *>(arg);
        self->last_rx_edge_us_ = static_cast<uint32_t>(esp_timer_get_time());
    }
    static void put32_(uint8_t *p, uint32_t value) {
        for (unsigned i=0; i<4; ++i) p[i] = value >> (8*i);
    }
    void record_(int value) {
        if (!trace_enabled_) return;
        if (trace_count_ == 192) { ++trace_dropped_; return; }
        auto *p = trace_ + 12 + trace_count_++ * 6;
        put32_(p, static_cast<uint32_t>(esp_timer_get_time()));
        p[4] = value & 255; p[5] = (static_cast<uint16_t>(value) >> 8);
    }
    bool trace_enabled_{false};
    uint32_t rx_byte_count_{0};
    int tx_monitor_pin_{-1};
    volatile uint32_t tx_edges_{0};
    int trace_rx_pin_{-1};
    uint32_t last_pin_sample_{0};
    uint32_t trace_count_{0}, trace_sequence_{0}, trace_dropped_{0};
    uint8_t trace_[12 + 192 * 6]{};
    uart::UARTDevice* uart_device_;
    GPIOPin* re_de_pin_;
    int rx_idle_pin_{-1};
    bool edge_detection_ready_{false};
    volatile uint32_t last_rx_edge_us_{0};
};

}
