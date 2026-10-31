namespace WeatherWallpaperPromptGenerator.Core;

public static class PromptCatalog
{
    public static IReadOnlyList<string> WeatherOptions { get; } =
    [
        "晴朗", "晴時多雲", "多雲", "陰天", "薄霧", "濃霧", "霾",
        "毛毛雨", "小雨", "中雨", "大雨", "豪雨", "陣雨", "雷陣雨", "雷暴",
        "強風", "颱風", "熱浪", "寒流", "下雪", "大雪", "暴雪", "雨夾雪",
        "凍雨", "冰雹", "沙塵暴"
    ];

    public static IReadOnlyList<string> PeriodOptions { get; } =
        ["上午", "下午", "傍晚", "晚上", "深夜", "清晨"];

    public static IReadOnlyList<string> StyleOptions { get; } =
        ["針織品", "色鉛筆", "Q版紙雕", "Q版漫畫"];
}
