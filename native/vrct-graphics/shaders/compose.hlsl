// VR UI compose pass: captured BGRA x CPU-built mask -> overlay texture.
// Bit-exact port of overlay.py transferCapture: pixels[..., 3] = mask, then the
// launcher intro (pending: launcher fully transparent; playing: introKeyAlpha).
// Rebuild the .cso files with build_shaders.cmd after editing (fxc, Windows SDK).

Texture2D<float4> captured : register(t0);
Texture2D<float> mask : register(t1);

cbuffer Params : register(b0)
{
    uint intro;   // 0 idle, 1 pending, 2 playing
    uint3 pad;
    int4 rect;    // launcher x0, y0, x1, y1 in pixels
};

float4 vs_main(uint id : SV_VertexID) : SV_Position
{
    // One triangle covering the viewport.
    float2 uv = float2((id << 1) & 2, id & 2);
    return float4(uv * float2(2, -2) + float2(-1, 1), 0, 1);
}

uint absdiff(uint a, uint b)
{
    return a > b ? a - b : b - a;
}

float4 ps_main(float4 pos : SV_Position) : SV_Target
{
    int2 p = int2(pos.xy);
    float4 c = captured.Load(int3(p, 0));
    uint a = (uint)round(mask.Load(int3(p, 0)) * 255.0);
    if (intro != 0 && all(p >= rect.xy) && all(p < rect.zw))
    {
        if (intro == 1)
            return float4(0, 0, 0, 0);
        uint3 v = (uint3)round(c.rgb * 255.0);
        uint3 k = (uint3)round(captured.Load(int3(rect.xy, 0)).rgb * 255.0);
        uint d = max(max(absdiff(v.r, k.r), absdiff(v.g, k.g)), absdiff(v.b, k.b));
        // _INTRO_ALPHA_LUT: clip((d - 4) * 255 // 16, 0, 255) in unsigned arithmetic.
        uint keyed = d > 4 ? min((d - 4) * 255 / 16, 255) : 0;
        a = min(a, keyed);
        if (a == 0)
            return float4(0, 0, 0, 0);  // cv2.copyTo: transparent pixels get colour 0 too
    }
    return float4(c.rgb, a / 255.0);
}
