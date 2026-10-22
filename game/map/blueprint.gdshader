shader_type canvas_item;

uniform vec4 base_color : source_color = vec4(0.035, 0.07, 0.13, 1.0);
uniform vec4 minor_color : source_color = vec4(0.30, 0.50, 0.85, 0.10);
uniform vec4 major_color : source_color = vec4(0.35, 0.60, 0.95, 0.22);
uniform float cell = 20.0;
uniform float major_every = 5.0;

varying vec2 world_pos;

void vertex() {
	world_pos = (MODEL_MATRIX * vec4(VERTEX, 0.0, 1.0)).xy;
}

float grid_line(vec2 p, float size) {
	vec2 coord = p / size;
	vec2 g = abs(fract(coord - 0.5) - 0.5) / max(fwidth(coord), vec2(1e-5));
	return 1.0 - min(min(g.x, g.y), 1.0);
}

void fragment() {
	vec3 col = base_color.rgb;
	col = mix(col, minor_color.rgb, grid_line(world_pos, cell) * minor_color.a);
	col = mix(col, major_color.rgb, grid_line(world_pos, cell * major_every) * major_color.a);
	COLOR = vec4(col, base_color.a);
}
