// =============================================================================
// weight_mem.sv
// Weight store, read as a stream. One word = COLS weights (one per mac_array
// column), stored in the order mme reads them.
// Owner:     Michael
// Latency:   about RD_LAT + 1 cycles from rd_start to the first w_valid
// Primitive: URAM288 (mem_bank STYLE 2), plus a small FIFO in fabric
// Part of:   mme
//
// How it works:
// - Write port (weight_loader, at boot): we, waddr, wdata.
// - rd_start with rd_addr starts a stream at that address. Words then come
//   out on w_valid / w_data in increasing address order, one per cycle while
//   w_ready is 1, and stop at the last address (DEPTH - 1).
// - A new rd_start restarts the stream anywhere, even mid-stream: words
//   already read for the old stream are thrown away.
// - The memory has RD_LAT cycles of latency, so reads are issued ahead into
//   a FIFO of RD_LAT + 4 words. A read is only issued if there is a FIFO slot
//   for it, so w_ready can drop at any time and nothing is lost.
// - Stream rule: once w_valid is 1, w_data holds until it is taken.
// =============================================================================
`timescale 1ns / 1ps

module weight_mem
  import accel_pkg::*;
#(
  parameter int WORD_W = COLS * DW,             // 64: 8 columns x INT8
  parameter int DEPTH  = 4096,                  // words (full model ~200K; small for sim)
  parameter int RD_LAT = 4,                     // memory read latency (URAM cascade needs pipeline)
  parameter int STYLE  = 2,                     // 2 = URAM; 0/1 allowed for small tests
  parameter int AW     = (DEPTH > 1) ? $clog2(DEPTH) : 1   // derived, don't override
)(
  input  logic              clk,
  input  logic              rst_n,

  // write port (weight_loader)
  input  logic              we,
  input  logic [AW-1:0]     waddr,
  input  logic [WORD_W-1:0] wdata,

  // read stream
  input  logic              rd_start,     // 1 = start a new stream at rd_addr
  input  logic [AW-1:0]     rd_addr,
  output logic              w_valid,
  input  logic              w_ready,
  output logic [WORD_W-1:0] w_data
);

  localparam int FD = RD_LAT + 4;                 // FIFO depth
  localparam int PW = $clog2(FD);                 // FIFO pointer width
  localparam int CW = $clog2(FD + 1) + 1;         // counter width (with room for a sum)
  localparam int EW = $clog2(RD_LAT + 2);         // stream id width: more ids than reads in flight

  // ---- memory ----------------------------------------------------------------
  logic              re;
  logic [AW-1:0]     raddr;
  logic [WORD_W-1:0] mdata;
  logic              mvalid;

  mem_bank #(.WORD_W(WORD_W), .DEPTH(DEPTH), .N_RD(1), .RD_LAT(RD_LAT), .STYLE(STYLE)) u_mem (
    .clk    (clk),
    .rst_n  (rst_n),
    .we     (we),
    .waddr  (waddr),
    .wdata  (wdata),
    .re     (re),
    .raddr  (raddr),
    .rdata  (mdata),
    .rvalid (mvalid)
  );

  // ---- stream state ------------------------------------------------------------
  logic              running;            // still have addresses to read
  logic [CW-1:0]     inflight;           // reads issued, not back yet
  logic [CW-1:0]     count;              // words in the FIFO
  logic [EW-1:0]     sid;                // stream id, changes on every rd_start
  logic [EW-1:0]     tag [RD_LAT];       // stream id of each read in flight (lines up with mvalid)
  logic [WORD_W-1:0] fifo [FD];
  logic [PW-1:0]     wp, rp;

  // issue a read only if it will have a FIFO slot when it comes back
  assign re = running && !rd_start && ((count + inflight) < FD);

  // keep a returning word only if it belongs to the current stream
  logic accept, pop;
  assign accept = mvalid && !rd_start && (tag[RD_LAT-1] == sid);
  assign pop    = w_valid && w_ready && !rd_start;

  assign w_valid = (count != 0);
  assign w_data  = fifo[rp];

  // stream id travels alongside each read
  always_ff @(posedge clk) begin
    tag[0] <= sid;
    for (int i = 1; i < RD_LAT; i++) tag[i] <= tag[i-1];
  end

  always_ff @(posedge clk) begin
    if (!rst_n) begin
      running  <= 1'b0;
      inflight <= '0;
      count    <= '0;
      wp       <= '0;
      rp       <= '0;
      sid      <= '0;
      raddr    <= '0;
    end else begin
      // reads in flight: +1 per issue, -1 per return (old-stream returns count too)
      inflight <= inflight + CW'(re) - CW'(mvalid);

      if (rd_start) begin
        // new stream: flush the FIFO, new id so old reads get dropped
        running <= 1'b1;
        raddr   <= rd_addr;
        sid     <= sid + 1'b1;
        count   <= '0;
        wp      <= '0;
        rp      <= '0;
      end else begin
        if (re) begin
          raddr <= raddr + 1'b1;
          if (raddr == AW'(DEPTH - 1)) running <= 1'b0;   // that was the last address
        end
        if (accept) begin
          fifo[wp] <= mdata;
          wp <= (wp == PW'(FD - 1)) ? '0 : wp + 1'b1;
        end
        if (pop)
          rp <= (rp == PW'(FD - 1)) ? '0 : rp + 1'b1;
        count <= count + CW'(accept) - CW'(pop);
      end
    end
  end

endmodule
