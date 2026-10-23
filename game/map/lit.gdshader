shader_type canvas_item;
// 监听聚光：warm = 1 是监听者所在房间的原色暖光，warm = 0 是青色单色；light 控制亮度。

uniform float light : hint_range(0.0, 1.0) = 1.0;
uniform float warm : hint_range(0.0, 1.0) = 1.0;
uniform vec3 shade_dark : source_color = vec3(0.012, 0.035, 0.045);
uniform vec3 shade_light : source_color = vec3(0.30, 0.50, 0.52);
uniform vec3 warm_tint : source_color = vec3(1.08, 0.97, 0.84);

void fragment() {
	vec4 c = COLOR;
	float l = dot(c.rgb, vec3(0.299, 0.587, 0.114));
	vec3 mono = mix(shade_dark, shade_light, smoothstep(0.02, 0.8, l));
	vec3 lit = c.rgb * warm_tint;
	COLOR = vec4(mix(mono, lit, warm) * light, c.a);
}
