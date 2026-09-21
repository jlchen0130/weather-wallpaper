using WeatherWallpaperPromptGenerator.Core;

var prompt = PromptBuilder.Generate(new PromptOptions("颱風", "深夜", "高雄", "中秋節", "Q版紙雕"));

Assert(PromptCatalog.WeatherOptions.Count >= 20, "weather catalog should be comprehensive");
Assert(PromptCatalog.PeriodOptions.SequenceEqual(["上午", "下午", "傍晚", "晚上", "深夜", "清晨"]), "period order must match the product requirement");
Assert(PromptCatalog.StyleOptions.SequenceEqual(["針織品", "色鉛筆", "Q版紙雕", "Q版漫畫"]), "style options must match the product requirement");
Assert(prompt.Contains("高雄", StringComparison.Ordinal), "prompt should contain the city");
Assert(prompt.Contains("颱風", StringComparison.Ordinal), "prompt should contain the weather");
Assert(prompt.Contains("中秋節", StringComparison.Ordinal), "prompt should contain the festival");
Assert(prompt.Contains("完整景點與地標清單全部納入", StringComparison.Ordinal), "prompt should require all researched landmarks");
Assert(prompt.Contains("不可杜撰", StringComparison.Ordinal), "prompt should reject invented landmarks");
Assert(prompt.Contains("PNG", StringComparison.Ordinal), "prompt should request PNG output");

var noFestivalPrompt = PromptBuilder.Generate(new PromptOptions("晴朗", "清晨", "京都", "", "色鉛筆"));
Assert(noFestivalPrompt.Contains("無指定節慶", StringComparison.Ordinal), "empty festival should be supported");

try
{
    PromptBuilder.Generate(new PromptOptions("晴朗", "上午", "", "", "針織品"));
    throw new InvalidOperationException("blank city should fail validation");
}
catch (ArgumentException)
{
}

Console.WriteLine("Smoke tests passed.");

static void Assert(bool condition, string message)
{
    if (!condition) throw new InvalidOperationException(message);
}
