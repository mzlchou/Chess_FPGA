// =============================================================================
// mme.sv
// Matmul engine. Runs one matmul command on the shared mac_array: COLS output
// columns per pass, one input feature per step, then drains the pass one
// column per beat.
// Owner:     Michael
// Modes:     MODE_AXW     activation x weight (projections, MLP, heads)
//            MODE_AXA_QK  activation x activation, Q.K^T scores
//            MODE_AXA_AV and MODE_GAB_MIX are not built yet (command just finishes)
// Primitive: LANES * COLS DSP48E2 (mac_array), the rest is fabric
// Part of:   core
//
// Command (latched on start):
//   n_steps  input features K, one step each
//   n_cols   outputs N. passes = ceil(N / COLS); padded columns are computed, never drained
//   a_base   lane bank address of feature 0 (X, or Q for AXA_QK)
//   c_base   AXW:    weight_mem address of pass 0 step 0. Pass-major: pass p step k is c_base + p*n_steps + k
//            AXA_QK: column bank address of feature 0 of K
//   p_base   param bank address of pass 0's bias word (one word = COLS biases per pass)
//   bias_en  1 = add the bias in the drain
//
// Pass p, step k:  lane word = lane bank[a_base + k]
//   AXW:    column j = INT8 j of the next weight word in the stream
//   AXA_QK: column j = lane (p*COLS + j) of column bank[c_base + k] (key square p*COLS + j)
//
// Drain (decision 2): when the last step of a pass is in acc, the grid stops and
// sends one beat per column:  d_data[s] = acc[j][s] + bias[j],  d_col = p*COLS + j,
// d_last on the last column of the command. row_max[s] is the max of every
// d_data[s] in the command, valid at done (softmax needs it for AXA_QK).
// done pulses once the last beat has been taken.
// =============================================================================
`timescale 1ns / 1ps

module mme
  import accel_pkg::*;
#(
  parameter int LANES  = accel_pkg::LANES,
  parameter int COLS   = accel_pkg::COLS,
  parameter int ACT_W  = 16,                 // activation: lane words and K words (N11)
  parameter int WT_W   = 8,                  // weight: INT8
  parameter int BIAS_W = 32,                 // bias at accumulator scale (N5)
  parameter int A_W    = MAC_A_W,
  parameter int W_W    = MAC_W_W,
  parameter int ACC_W  = MAC_ACC_W,
  parameter int A_LAT  = accel_pkg::RD_LAT,  // lane and column bank read latency
  parameter int P_LAT  = accel_pkg::RD_LAT,  // param bank read latency
  parameter int ADDR_W = 16,                 // address width of every port
  parameter int N_W    = 12                  // n_steps / n_cols width
)(
  input  logic clk,
  input  logic rst_n,

  // command
  input  logic              start,           // 1 cycle, only while !busy
  input  logic [1:0]        mode,
  input  logic [N_W-1:0]    n_steps,         // >= 1
  input  logic [N_W-1:0]    n_cols,          // >= 1 (AXA_QK: <= LANES)
  input  logic [ADDR_W-1:0] a_base,
  input  logic [ADDR_W-1:0] c_base,
  input  logic [ADDR_W-1:0] p_base,
  input  logic              bias_en,
  output logic              busy,
  output logic              done,

  // lane bank read (X, or Q)
  output logic                        a_re,
  output logic [ADDR_W-1:0]           a_raddr,
  input  logic [LANES-1:0][ACT_W-1:0] a_rdata,

  // column bank read (K), AXA_QK only
  output logic                        c_re,
  output logic [ADDR_W-1:0]           c_raddr,
  input  logic [LANES-1:0][ACT_W-1:0] c_rdata,

  // weight stream (weight_mem), AXW only
  output logic                       w_rd_start,
  output logic [ADDR_W-1:0]          w_rd_addr,
  input  logic                       w_valid,
  output logic                       w_ready,
  input  logic [COLS-1:0][WT_W-1:0]  w_data,

  // param bank read (bias), one word per pass
  output logic                         p_re,
  output logic [ADDR_W-1:0]            p_raddr,
  input  logic [COLS-1:0][BIAS_W-1:0]  p_rdata,

  // drain stream
  output logic                        d_valid,
  input  logic                        d_ready,
  output logic [LANES-1:0][ACC_W-1:0] d_data,
  output logic [N_W-1:0]              d_col,
  output logic                        d_last,

  output logic [LANES-1:0][ACC_W-1:0] row_max
);

  localparam int LAND_N = A_LAT + 3;          // cycles after the last step until its sum is in acc
  localparam int JW     = $clog2(COLS + 1);   // drain column counter
  localparam int LW     = $clog2(LAND_N + 1); // land counter

  typedef enum logic [2:0] {S_IDLE, S_STEP, S_LAND, S_DRAIN, S_FIN} state_t;
  state_t st;

  // ---- command registers ---------------------------------------------------------
  logic [1:0]        mode_r;
  logic [N_W-1:0]    ns_r, nc_r;
  logic [ADDR_W-1:0] a_base_r, c_base_r;
  logic              bias_en_r;

  // ---- pass state ----------------------------------------------------------------
  logic [N_W-1:0]    step;                    // k in this pass
  logic [N_W-1:0]    col0;                    // p * COLS, first column of this pass
  logic [LW-1:0]     land_cnt;
  logic [JW-1:0]     dj;                      // column being drained
  logic              rm_first;                // next beat is the first of the command

  logic is_axw;
  assign is_axw = (mode_r == MODE_AXW);

  logic last_pass;                            // this pass holds column n_cols-1
  logic [N_W-1:0] ncp;                        // columns to drain this pass
  assign last_pass = ({1'b0, col0} + COLS) >= {1'b0, nc_r};
  assign ncp       = last_pass ? (nc_r - col0) : N_W'(COLS);

  // ---- step issue ----------------------------------------------------------------
  // AXW waits for a weight word. Not on the rd_start cycle: w_valid there can
  // still be a word of the old stream.
  logic fire;
  assign w_ready = (st == S_STEP) && is_axw && !w_rd_start;
  assign fire    = (st == S_STEP) && (!is_axw || (w_valid && !w_rd_start));
  assign a_re    = fire;
  assign a_raddr = a_base_r + ADDR_W'(step);
  assign c_re    = fire && !is_axw;
  assign c_raddr = c_base_r + ADDR_W'(step);
  assign busy    = (st != S_IDLE);

  // ---- step pipeline: lines the weight word and the first-step flag up with the bank data
  logic                 pv   [A_LAT];
  logic                 pclr [A_LAT];
  logic [COLS*WT_W-1:0] pw   [A_LAT];

  always_ff @(posedge clk) begin
    pw[0]   <= w_data;
    pclr[0] <= (step == '0);
    for (int i = 1; i < A_LAT; i++) begin
      pw[i]   <= pw[i-1];
      pclr[i] <= pclr[i-1];
    end
    if (!rst_n) begin
      for (int i = 0; i < A_LAT; i++) pv[i] <= 1'b0;
    end else begin
      pv[0] <= fire;
      for (int i = 1; i < A_LAT; i++) pv[i] <= pv[i-1];
    end
  end

  // ---- mac_array operands ----------------------------------------------------------
  logic [LANES-1:0][A_W-1:0]  mac_a;
  logic [COLS-1:0][W_W-1:0]   mac_w;
  logic [LANES*ACT_W-1:0]     c_flat;
  logic [COLS*WT_W-1:0]       w_last;
  assign c_flat = c_rdata;
  assign w_last = pw[A_LAT-1];

  for (genvar s = 0; s < LANES; s++) begin : g_a
    assign mac_a[s] = {{(A_W-ACT_W){a_rdata[s][ACT_W-1]}}, a_rdata[s]};   // sign extend
  end

  for (genvar j = 0; j < COLS; j++) begin : g_w
    logic [WT_W-1:0]  wj;
    logic [ACT_W-1:0] kj;
    assign wj = w_last[j*WT_W +: WT_W];
    assign kj = c_flat[(col0 + j)*ACT_W +: ACT_W];                   // key square col0 + j
    assign mac_w[j] = is_axw ? {{(W_W-WT_W){wj[WT_W-1]}}, wj}
                             : {{(W_W-ACT_W){kj[ACT_W-1]}}, kj};
  end

  logic [COLS-1:0][LANES-1:0][ACC_W-1:0] acc;

  mac_array #(.LANES(LANES), .COLS(COLS), .A_W(A_W), .W_W(W_W), .ACC_W(ACC_W)) u_mac (
    .clk       (clk),
    .rst_n     (rst_n),
    .en        (pv[A_LAT-1]),
    .clear     (pclr[A_LAT-1]),
    .a         (mac_a),
    .w         (mac_w),
    .col_a_sel (1'b0),
    .a_col     ('0),
    .acc       (acc)
  );

  // ---- bias (decision 3): read at the start of each pass, used in its drain ----------
  logic                   pbv [P_LAT];
  logic                   bias_ok;
  logic [COLS*BIAS_W-1:0] bias_r;

  always_ff @(posedge clk) begin
    if (pbv[P_LAT-1]) bias_r <= p_rdata;
    if (!rst_n) begin
      for (int i = 0; i < P_LAT; i++) pbv[i] <= 1'b0;
      bias_ok <= 1'b0;
    end else begin
      pbv[0] <= p_re;
      for (int i = 1; i < P_LAT; i++) pbv[i] <= pbv[i-1];
      if (p_re)                bias_ok <= 1'b0;
      else if (pbv[P_LAT-1])   bias_ok <= 1'b1;
    end
  end

  // ---- drain adder: acc column dj + its bias, 64 lanes ---------------------------------
  logic [COLS*LANES*ACC_W-1:0] acc_flat;
  logic [LANES*ACC_W-1:0]      acc_col;
  logic [BIAS_W-1:0]           b_col;
  logic [ACC_W-1:0]            b_ext;
  logic [LANES-1:0][ACC_W-1:0] sum;
  assign acc_flat = acc;
  assign acc_col  = acc_flat[dj*LANES*ACC_W +: LANES*ACC_W];
  assign b_col    = bias_r[dj*BIAS_W +: BIAS_W];
  assign b_ext    = bias_en_r ? {{(ACC_W-BIAS_W){b_col[BIAS_W-1]}}, b_col} : '0;

  for (genvar s = 0; s < LANES; s++) begin : g_sum
    assign sum[s] = acc_col[s*ACC_W +: ACC_W] + b_ext;
  end

  logic load;
  assign load = (st == S_DRAIN) && (!d_valid || d_ready);

  // ---- control ---------------------------------------------------------------------
  always_ff @(posedge clk) begin
    // data registers (not reset)
    if (load) begin
      d_data <= sum;
      d_col  <= col0 + N_W'(dj);
      d_last <= last_pass && (N_W'(dj) == ncp - 1'b1);
      for (int s = 0; s < LANES; s++)
        if (rm_first || $signed(sum[s]) > $signed(row_max[s])) row_max[s] <= sum[s];
    end

    if (!rst_n) begin
      st         <= S_IDLE;
      d_valid    <= 1'b0;
      done       <= 1'b0;
      w_rd_start <= 1'b0;
      p_re       <= 1'b0;
    end else begin
      done       <= 1'b0;
      w_rd_start <= 1'b0;
      p_re       <= 1'b0;
      if (d_valid && d_ready) d_valid <= 1'b0;
      if (load)               d_valid <= 1'b1;

      case (st)
        S_IDLE: if (start) begin
          mode_r    <= mode;
          ns_r      <= n_steps;
          nc_r      <= n_cols;
          a_base_r  <= a_base;
          c_base_r  <= c_base;
          bias_en_r <= bias_en;
          step      <= '0;
          col0      <= '0;
          rm_first  <= 1'b1;
          if (mode == MODE_AXW || mode == MODE_AXA_QK) begin
            st         <= S_STEP;
            w_rd_start <= (mode == MODE_AXW);   // one stream for the whole command (pass-major)
            w_rd_addr  <= c_base;
            p_re       <= bias_en;
            p_raddr    <= p_base;
          end else begin
            st <= S_FIN;                        // AXA_AV / GAB_MIX: not built yet
            // synthesis translate_off
            $error("mme: mode %0d not built yet", mode);
            // synthesis translate_on
          end
        end

        S_STEP: if (fire) begin
          if (step == ns_r - 1'b1) begin
            st       <= S_LAND;
            land_cnt <= '0;
          end else begin
            step <= step + 1'b1;
          end
        end

        S_LAND: begin                           // wait for the last step to reach acc, and the bias
          if (land_cnt != LW'(LAND_N - 1)) land_cnt <= land_cnt + 1'b1;
          else if (!bias_en_r || bias_ok) begin
            st <= S_DRAIN;
            dj <= '0;
          end
        end

        S_DRAIN: if (load) begin
          rm_first <= 1'b0;
          if (N_W'(dj) == ncp - 1'b1) begin
            if (last_pass) st <= S_FIN;
            else begin                          // next pass: weights keep streaming in order
              st      <= S_STEP;
              step    <= '0;
              col0    <= col0 + N_W'(COLS);
              p_re    <= bias_en_r;
              p_raddr <= p_raddr + 1'b1;          // next pass's bias word
            end
          end else begin
            dj <= dj + 1'b1;
          end
        end

        S_FIN: if (!d_valid) begin              // last beat taken
          done <= 1'b1;
          st   <= S_IDLE;
        end

        default: st <= S_IDLE;
      endcase
    end
  end

endmodule
