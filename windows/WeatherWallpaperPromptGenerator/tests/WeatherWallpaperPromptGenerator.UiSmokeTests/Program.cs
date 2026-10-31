using System.Windows;
using System.Windows.Controls;
using WeatherWallpaperPromptGenerator.App;
using WeatherWallpaperPromptGenerator.Core;

namespace WeatherWallpaperPromptGenerator.UiSmokeTests;

internal static class Program
{
    [STAThread]
    private static void Main()
    {
        var application = new WeatherWallpaperPromptGenerator.App.App();
        application.InitializeComponent();
        var window = new MainWindow();
        window.Show();
        window.UpdateLayout();

        var weather = Require<ComboBox>(window, "WeatherComboBox");
        var period = Require<ComboBox>(window, "PeriodComboBox");
        var style = Require<ComboBox>(window, "StyleComboBox");
        var city = Require<TextBox>(window, "CityTextBox");
        var festival = Require<TextBox>(window, "FestivalTextBox");
        var output = Require<TextBox>(window, "PromptTextBox");

        Assert(window.IsVisible, "main window should be visible after Show");
        Assert(weather.Items.Count == PromptCatalog.WeatherOptions.Count, "weather combo should expose the full catalog");
        Assert(period.Items.Count == 6, "period combo should contain six items");
        Assert(style.Items.Count == 4, "style combo should contain four items");
        Assert(city.Text == "高雄", "city should have the documented default");
        Assert(string.IsNullOrEmpty(festival.Text), "festival should allow an empty value");
        Assert(output.Text.Contains("完整景點與地標清單全部納入", StringComparison.Ordinal), "generated prompt should require all verified landmarks");

        window.Close();
        application.Shutdown();
        Console.WriteLine("WPF UI smoke tests passed.");
    }

    private static T Require<T>(FrameworkElement root, string name) where T : FrameworkElement
    {
        return root.FindName(name) as T
            ?? throw new InvalidOperationException($"Missing control: {name}");
    }

    private static void Assert(bool condition, string message)
    {
        if (!condition) throw new InvalidOperationException(message);
    }
}
