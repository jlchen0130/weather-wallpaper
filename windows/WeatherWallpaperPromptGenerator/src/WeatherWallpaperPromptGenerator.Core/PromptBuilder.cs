using System.Text;

namespace WeatherWallpaperPromptGenerator.Core;

public static class PromptBuilder
{
    private static readonly IReadOnlyDictionary<string, string> PeriodDescriptions =
        new Dictionary<string, string>
        {
            ["上午"] = "上午的明亮自然光，空氣清新，陰影柔和清楚",
            ["下午"] = "下午的溫暖日光，光線飽滿，城市活動感明顯",
            ["傍晚"] = "傍晚金色時刻，橙粉天空與逐漸亮起的城市燈光",
            ["晚上"] = "夜晚藍黑天空，溫暖街燈與建築燈光形成清楚層次",
            ["深夜"] = "深夜寧靜氛圍，深藍天空、稀疏燈光與低密度活動",
            ["清晨"] = "日出前後的清晨薄光，淡藍與柔粉天空，城市逐漸甦醒"
        };

    private static readonly IReadOnlyDictionary<string, string> StyleDescriptions =
        new Dictionary<string, string>
        {
            ["針織品"] = "高品質手工針織與鉤針毛線公仔風格；建築、雲朵、樹木、人物與交通工具都有可見的毛線纖維、縫線與柔軟立體質感",
            ["色鉛筆"] = "精緻色鉛筆插畫風格；保留紙張紋理、細膩筆觸、柔和疊色與童話般的自然光影",
            ["Q版紙雕"] = "精緻 Q 版紙雕與立體剪紙風格；多層紙材、清楚切邊、柔和投影、微縮立體景深與可愛比例",
            ["Q版漫畫"] = "精緻 Q 版漫畫風格；乾淨線稿、明快配色、可愛比例、自然表情、清楚景深與具故事感的城市日常"
        };

    public static string Generate(PromptOptions options)
    {
        var city = Required(options.City, "城市");
        var weather = Required(options.Weather, "天氣");
        var period = Required(options.Period, "時段");
        var style = Required(options.Style, "畫風");
        var festival = string.IsNullOrWhiteSpace(options.Festival)
            ? "無指定節慶；維持符合當地季節的日常城市氛圍"
            : options.Festival.Trim();

        if (!PromptCatalog.WeatherOptions.Contains(weather))
            throw new ArgumentException("不支援的天氣選項。", nameof(options));
        if (!PromptCatalog.PeriodOptions.Contains(period))
            throw new ArgumentException("不支援的時段選項。", nameof(options));
        if (!PromptCatalog.StyleOptions.Contains(style))
            throw new ArgumentException("不支援的畫風選項。", nameof(options));

        var prompt = new StringBuilder();
        prompt.AppendLine("請建立一張可供 Android 動態桌布使用的高解析度直式 PNG 插畫，比例 9:16。不要產生影片或動畫檔；動態效果將由 Android WallpaperService 疊加。");
        prompt.AppendLine();
        prompt.AppendLine("【場景條件】");
        prompt.AppendLine($"- 城市：{city}");
        prompt.AppendLine($"- 天氣：{weather}");
        prompt.AppendLine($"- 時段：{period}；{PeriodDescriptions[period]}");
        prompt.AppendLine($"- 節慶：{festival}");
        prompt.AppendLine($"- 畫風：{style}；{StyleDescriptions[style]}");
        prompt.AppendLine();
        prompt.AppendLine("【城市景點與地標，必須先查證】");
        prompt.AppendLine($"1. 使用可用的網路搜尋、地圖或可靠旅遊資料，查找「{city}」境內所有公開可辨識的主要景點、歷史建築、自然地標、文化設施與代表性城市設施。");
        prompt.AppendLine("2. 先在內部整理並去除重複、已拆除、名稱相同或不屬於該城市的項目；資料不足時要明確要求使用者補充，不可杜撰地標。");
        prompt.AppendLine("3. 將查證後的完整景點與地標清單全部納入同一幅圖。數量很多時，以遠景天際線、中景街區、近景微縮模型、河岸、山景或分層紙景方式安排，保持每個地標仍可辨識，不可任意省略。");
        prompt.AppendLine("4. 地標需自然融入城市空間，不要做成方格拼貼、旅遊海報或彼此比例完全相同的圖鑑。");
        prompt.AppendLine();
        prompt.AppendLine("【構圖與氣氛】");
        prompt.AppendLine("- 採略高視角的廣角城市全景，建立清楚的前景、中景與遠景，讓大量地標仍有秩序且不互相遮擋。");
        prompt.AppendLine($"- 天空、地面、植被、人物活動與光影必須符合「{weather}」及「{period}」，不可只放一個天氣圖示代替真實環境效果。");
        prompt.AppendLine("- 加入適量 Q 版居民與日常活動，使場景有生活感，但人物不可遮住主要地標。");
        prompt.AppendLine("- 頂部保留乾淨、明亮且低細節的天空區域，供手機時鐘、日期及狀態圖示顯示。");
        prompt.AppendLine("- 畫面需完整、精緻、清楚，不要過暗、過度模糊、裁切主要地標或使用無法辨識的抽象背景。");
        prompt.AppendLine();
        prompt.AppendLine("【禁止項目】");
        prompt.AppendLine("不要在圖片中加入城市名稱、景點名稱、標題、說明文字、Logo、浮水印、手機介面、時鐘、日期、溫度、電量、訊號、App 圖示或邊框。不要捏造不存在的建築，也不要把其他城市的地標混入。");
        prompt.AppendLine();
        prompt.Append("只輸出最終圖片；若目前使用的 AI agent 不能直接產圖，則輸出一份已包含完整地標清單、可直接交給圖像生成模型的最終提示詞，不要省略上述限制。");
        return prompt.ToString();
    }

    private static string Required(string value, string fieldName)
    {
        if (string.IsNullOrWhiteSpace(value))
            throw new ArgumentException($"請填寫{fieldName}。", fieldName);
        return value.Trim();
    }
}
