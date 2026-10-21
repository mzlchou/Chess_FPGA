// =============================================================================
// accel_pkg.sv
// Shared parameters and types for the chess accelerator.
// Owner:  Michael
// Use:    every module adds `import accel_pkg::*;`
// Values marked TBD are placeholders until Matthew got his info meow
// =============================================================================
`timescale 1ns / 1ps

package accel_pkg;

  // ---------------------------------------------------------------------------
  // Model dimensions (from Matt model)
  // ---------------------------------------------------------------------------
  localparam int N_TOK    = 64;                 // tokens: one per board square
  localparam int D_MODEL  = 128;                // TBD features per token (means dimension of the model -> 128 numbers describe each square in the model)
  localparam int N_HEADS  = 4;                  // TBD attention heads (means x heads, each looking at the board a diff way)
  localparam int D_HEAD   = D_MODEL / N_HEADS;  // features per head (x numbers each head works w)
  localparam int D_FF     = 256;                // TBD MLP hidden width (dimension of feed forward layer)
  localparam int N_LAYERS = 4;                  // TBD transformer blocks (self explanatory)
  localparam int F_IN     = 112;                // TBD input features per square (features in ie how many numbers describe each square in the input)

  // ---------------------------------------------------------------------------
  // Hardware shape 
  // ---------------------------------------------------------------------------
  localparam int LANES  = N_TOK;  // one MAC lane per square (self explanatory)
  localparam int COLS   = 8;      // output columns computed per pass (self explanatory)
  localparam int DW     = 8;      // weight and activation width: INT8 (self explanatory)
  localparam int ACCW   = 32;     // accumulator width: INT32 (self explanatory)
  localparam int RD_LAT = 2;      // memory read latency, in clock cycles (read latency is how many cycles it takes to get data back from memory after you ask for it)
  localparam int AXIS_W = 64;     // DMA stream width, in bits (axi stream width is how many bits the DMA sends in one beat)

  // Derived from the above. 
  localparam int ACT_WORD_W     = LANES * DW;           // 512: bits in one act_buf word (activation word width )
  localparam int BEATS_PER_WORD = ACT_WORD_W / AXIS_W;  // 8: DMA beats per act_buf word (how many DMA beats are needed to transfer one activation word)
  localparam int FEAT_AW        = $clog2(D_MODEL);      // 7: address bits to pick a feature (feature address width )

  // ---------------------------------------------------------------------------
  // Types
  // ---------------------------------------------------------------------------
  typedef logic signed [DW-1:0]   act_t;       // one INT8 value (activation type)
  typedef logic signed [ACCW-1:0] acc_t;       // one INT32 sum (accumulator type)
  typedef act_t [LANES-1:0]       act_word_t;  // one feature for all 64 squares
  typedef act_t [COLS-1:0]        wgt_word_t;  // one weight_mem word

endpackage
