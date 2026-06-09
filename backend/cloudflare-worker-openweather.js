export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const lat = url.searchParams.get("lat");
    const lon = url.searchParams.get("lon");
    const units = url.searchParams.get("units") || "metric";

    if (!lat || !lon) {
      return json({ error: "Missing lat/lon" }, 400);
    }
    if (!env.OPENWEATHER_API_KEY) {
      return json({ error: "OPENWEATHER_API_KEY is not configured" }, 500);
    }

    const api = new URL("https://api.openweathermap.org/data/2.5/weather");
    api.searchParams.set("lat", lat);
    api.searchParams.set("lon", lon);
    api.searchParams.set("units", units);
    api.searchParams.set("appid", env.OPENWEATHER_API_KEY);

    const response = await fetch(api);
    const body = await response.json();
    if (!response.ok) {
      return json({ error: body.message || "OpenWeather error" }, response.status);
    }

    return json({
      weather: body.weather?.[0]?.main || "Clouds",
      temp_min: body.main?.temp_min ?? 27,
      temp_max: body.main?.temp_max ?? 32,
      city: body.name || "",
      country: body.sys?.country || ""
    });
  }
};

function json(value, status = 200) {
  return new Response(JSON.stringify(value), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
      "access-control-allow-origin": "*"
    }
  });
}
