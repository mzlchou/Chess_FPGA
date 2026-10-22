# =============================================================================
# create_project.tcl
# Rebuilds the local Vivado project from the sources in this repo.
#
# Usage, in the Vivado Tcl Console:
#     source C:/chess/accelerator/scripts/create_project.tcl
#
# It only ever deletes and recreates accelerator/vivado/chess_accel/, never your sources.
# =============================================================================

# ---- Settings ---------------------------------------------------------------
set proj_name  chess_accel
set part       xck26-sfvc784-2LV-c
set board_part xilinx.com:kr260_som:part0:1.1
set design_top axis_test         ;# replaced by the block design wrapper if bd/ has one
set sim_top    tb_axis_test
set want_ver   2023.2
set bd_name    design_1
set bd_script  loopback.tcl     ;# block design to rebuild, in bd/

# ---- Find the accelerator folder --------------------------------------------
set root     [file normalize [file join [file dirname [info script]] ..]]
set proj_dir [file join $root vivado $proj_name]
puts "Accelerator: $root"
puts "Project dir: $proj_dir"

# ---- Check the Vivado version -----------------------------------------------
if {[version -short] ne $want_ver} {
    puts "WARNING: this repo is built with Vivado $want_ver, you are running [version -short]"
}

# ---- Make a fresh project ---------------------------------------------------
catch {close_sim -force}     ;# a loaded simulation keeps files open
catch {close_project}
create_project $proj_name $proj_dir -part $part -force
set_property board_part $board_part [current_project]

# ---- Design sources: every .sv and .v one folder below rtl/ -----------------
set rtl_files [glob -nocomplain [file join $root rtl * *.sv] [file join $root rtl * *.v]]
if {[llength $rtl_files] > 0} {
    add_files -fileset sources_1 -norecurse $rtl_files
}
set_property include_dirs [list [file join $root rtl common]] [get_filesets sources_1]

# ---- Simulation sources: every .sv in tb/ -----------------------------------
set tb_files [glob -nocomplain [file join $root tb *.sv]]
if {[llength $tb_files] > 0} {
    add_files -fileset sim_1 -norecurse $tb_files
}
set_property include_dirs [list [file join $root rtl common]] [get_filesets sim_1]

# ---- Block design: rebuild it from its exported Tcl, if there is one -------
set bd_tcl [file join $root bd $bd_script]
if {[file exists $bd_tcl]} {
    source $bd_tcl
    make_wrapper -files [get_files $bd_name.bd] -top
    add_files -norecurse [file join $proj_dir $proj_name.gen sources_1 bd $bd_name hdl ${bd_name}_wrapper.v]
    set design_top ${bd_name}_wrapper
}

# ---- Top modules and simulation settings ------------------------------------
set_property top     $design_top    [get_filesets sources_1]
set_property top     $sim_top       [get_filesets sim_1]
set_property top_lib xil_defaultlib [get_filesets sim_1]
set_property -name xsim.simulate.runtime -value all -objects [get_filesets sim_1]

update_compile_order -fileset sources_1
update_compile_order -fileset sim_1

puts "Done: [llength $rtl_files] design files, [llength $tb_files] testbenches, design top = $design_top."
puts "Project file: [file join $proj_dir $proj_name.xpr]"
