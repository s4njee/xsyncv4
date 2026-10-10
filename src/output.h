// File events stay structured until the client's formatting and ordering step.
#pragma once
#include "common.h"

struct OutputEvent {
  std::string code, path, source, target;
  u8 type = T_NONE;
  i64 size = 0, bytes = 0, time = 0;
  bool hardlink_target = false;
};
extern void (*g_output_sink)(const OutputEvent&);
bool output_enabled();
std::string output_escape(std::string_view name);
bool output_format_supported(std::string_view format);
bool output_format_has(std::string_view format, char escape);
void output_configure();
void output_start();
void output_event(OutputEvent event);
void output_text(std::string_view text);
// Plain file lines from an older peer, whose wire layout remains frozen.
void output_legacy(std::string_view text);
void output_flush();
// Record stdout failures without unwinding while UI/output locks are held.
void output_failure(int error);
int output_error();
void output_check();
