$fn = 30;

e = 0.001;
e2 = 2 * e;

slot_diam = 10;
slot_height = 13;
slot_tilt = 15;
slot_hole_diam = 6.625;
hole_depth = 11;
padding = 5;

grid_unit_x = 24;
grid_unit_y = 24.85; // grid_unit_x / cos(slot_tilt);
grid_cols = 9;
grid_rows = 9;
grid_width = grid_unit_x * grid_cols;
grid_height = grid_unit_y * grid_rows;

beam_width = 4;
rib_width = 1.5;
strut_height = 7;
rib_height = 1.5;

mount_diam = 12;
mount_inset = 1;
mount_offset = beam_width / 2 + mount_diam / 2 - mount_inset;

module mount(i, j, a) {
  y = i * grid_unit_y;
  x = j * grid_unit_x;
  hole_diam = 3;
  bevel_diam = 9;
  height = 3;

  translate([ x, y, 0 ]) rotate(a, [ 0, 0, 1 ])
      translate([ mount_offset, mount_offset, 0 ]) difference() {
    cylinder(height, d = mount_diam);
    // translate([ 0, 0, -e ]) cylinder(height + e2, r = hole_diam / 2);
    translate([ 0, 0, height - bevel_diam / 2 ])
        cylinder(bevel_diam / 2 + e, 0, d2 = bevel_diam);
  }
}

difference() {
  union() {
    for (i = [0:grid_rows]) {
      translate([ 0, i * grid_unit_y - rib_width / 2, 0 ]) {
        cube([
          grid_width,
          rib_width,
          strut_height,
        ]);
      }
      translate([ 0, i * grid_unit_y - beam_width / 2, 0 ]) {
        cube([
          grid_width,
          beam_width,
          rib_height,
        ]);
      }
    }
    for (j = [0:grid_cols]) {
      translate([ j * grid_unit_x - rib_width / 2, 0, 0 ]) {
        cube([
          rib_width,
          grid_height,
          strut_height,
        ]);
      }
      translate([ j * grid_unit_x - beam_width / 2, 0, 0 ]) {
        cube([
          beam_width,
          grid_height,
          rib_height,
        ]);
      }
    }
    for (i = [0:grid_rows]) {
      for (j = [0:grid_cols]) {
        translate([ j * grid_unit_x, i * grid_unit_y ]) {
          rotate(slot_tilt, [ -1, 0, 0 ]) translate([ 0, 0, -padding ])
              cylinder(slot_height + padding, slot_diam / 2, slot_diam / 2);
        }
      }
    }
    mount(0, 0, 0);
    mount(0, grid_cols, 90);
    mount(grid_rows, grid_cols, 180);
    mount(grid_rows, 0, 270);

    mid_row = floor(grid_rows / 2);
    mid_col = floor(grid_cols / 2);
    mount(mid_row, mid_col, 0);

    translate([ 0, 4 * grid_unit_y - beam_width / 2, 0 ]) {
      cube([
        grid_width,
        beam_width,
        strut_height,
      ]);
    }
    translate(
        [ mid_col * grid_unit_x + mount_offset + mount_diam / 2 - 1.5, 0, 0 ]) {
      cube([
        beam_width - rib_width,
        grid_height,
        strut_height,
      ]);
    }
  }
  union() {
    for (i = [0:grid_rows]) {
      for (j = [0:grid_cols]) {
        translate([ j * grid_unit_x, i * grid_unit_y ]) {
          rotate(slot_tilt, [ -1, 0, 0 ])
              translate([ 0, 0, slot_height - hole_depth ])
                  cylinder(slot_height, slot_hole_diam / 2, slot_hole_diam / 2);
        }
      }
    }
    translate([ -10, -10, -10 + e ]) cube([
      grid_width + 20,
      grid_height + 20,
      10,
    ]);
  }
}