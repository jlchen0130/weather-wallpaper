namespace WeatherWallpaperPromptGenerator.Core;

public sealed record PromptOptions(
    string Weather,
    string Period,
    string City,
    string Festival,
    string Style);
