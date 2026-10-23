shader_type canvas_item;
// 建筑外的地面：插画材质按世界坐标镜像平铺，压暗成和未点亮房间一致的青色调。

uniform sampler2D ground : source_color, filter_linear_mipmap, repeat_disable;
uniform bool has_ground = false;
uniform float tile = 200.0;
uniform float light = 0.42;
uniform vec3 base_color : source_color = vec3(0.050, 0.068, 0.078);
uniform vec3 shade_dark : source_color = vec3(0.012, 0.035, 0.045);
uniform vec3 shade_light : source_color = vec3(0.30, 0.50, 0.52);
uniform float keep_color = 0.35;

varying vec2 world_pos;

void vertex() {
	world_pos = (MODEL_MATRIX * vec4(VERTEX, 0.0, 1.0)).xy;
}

void fragment() {
	if (!has_ground) {
		COLOR = vec4(base_color, 1.0);
	} else {
		vec2 uv = world_pos / tile;
		uv = 1.0 - abs(mod(uv, 2.0) - 1.0);
		vec3 c = texture(ground, uv).rgb;
		float l = dot(c, vec3(0.299, 0.587, 0.114));
		vec3 mono = mix(shade_dark, shade_light, smoothstep(0.02, 0.8, l));
		COLOR = vec4(mix(mono, c, keep_color) * light, 1.0);
	}
}
