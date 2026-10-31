using System.Windows;
using System.Windows.Controls;
using WeatherWallpaperPromptGenerator.Core;

namespace WeatherWallpaperPromptGenerator.App;

public partial class MainWindow : Window
{
    private bool _initialized;

    public MainWindow()
    {
        InitializeComponent();
        WeatherComboBox.ItemsSource = PromptCatalog.WeatherOptions;
        PeriodComboBox.ItemsSource = PromptCatalog.PeriodOptions;
        StyleComboBox.ItemsSource = PromptCatalog.StyleOptions;
        ResetForm();
        _initialized = true;
        UpdatePrompt();
    }

    private void InputChanged(object sender, RoutedEventArgs e)
    {
        if (_initialized) UpdatePrompt();
    }

    private void GenerateClicked(object sender, RoutedEventArgs e) => UpdatePrompt(showValidation: true);

    private void CopyClicked(object sender, RoutedEventArgs e)
    {
        if (string.IsNullOrWhiteSpace(PromptTextBox.Text))
        {
            StatusTextBlock.Text = "尚無可複製的提示詞";
            return;
        }

        Clipboard.SetText(PromptTextBox.Text);
        StatusTextBlock.Text = "提示詞已複製到剪貼簿";
    }

    private void ResetClicked(object sender, RoutedEventArgs e)
    {
        ResetForm();
        UpdatePrompt();
    }

    private void ResetForm()
    {
        WeatherComboBox.SelectedItem = "晴朗";
        PeriodComboBox.SelectedItem = "下午";
        StyleComboBox.SelectedItem = "針織品";
        CityTextBox.Text = "高雄";
        FestivalTextBox.Text = string.Empty;
    }

    private void UpdatePrompt(bool showValidation = false)
    {
        try
        {
            var options = new PromptOptions(
                WeatherComboBox.SelectedItem?.ToString() ?? string.Empty,
                PeriodComboBox.SelectedItem?.ToString() ?? string.Empty,
                CityTextBox.Text,
                FestivalTextBox.Text,
                StyleComboBox.SelectedItem?.ToString() ?? string.Empty);

            PromptTextBox.Text = PromptBuilder.Generate(options);
            StatusTextBlock.Text = "提示詞已依目前欄位更新";
        }
        catch (ArgumentException error)
        {
            PromptTextBox.Text = string.Empty;
            StatusTextBlock.Text = error.Message;
            if (showValidation) MessageBox.Show(error.Message, "資料不完整", MessageBoxButton.OK, MessageBoxImage.Information);
        }
    }
}
