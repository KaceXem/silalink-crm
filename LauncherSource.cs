using System;
using System.Diagnostics;
using System.IO;
using System.Net.Sockets;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Animation;
using System.Windows.Shapes;

namespace SilaLinkControlCenter
{
    public class ServiceConfig
    {
        public string Name { get; set; }
        public string Description { get; set; }
        public int Port { get; set; }
        public string WorkDir { get; set; }
        public string Executable { get; set; }
        public string Arguments { get; set; }
    }

    public class App : Application
    {
        [STAThread]
        public static void Main()
        {
            App app = new App();
            app.Run(new MainWindow());
        }
    }

    public class MainWindow : Window
    {
        private ServiceConfig[] services = new ServiceConfig[]
        {
            new ServiceConfig {
                Name = "OmniRoute AI Proxy",
                Description = "Moteur d'infÃ©rence LLM B2B (Port 20128)",
                Port = 20128,
                WorkDir = @"C:\Users\USER\Desktop\4 espace\OmniRoute-release-v3.8.51",
                Executable = "cmd.exe",
                Arguments = "/c npm start"
            },
            new ServiceConfig {
                Name = "Backend FastAPI",
                Description = "Pipeline SQLite & API Gmail (Port 8000)",
                Port = 8000,
                WorkDir = @"C:\Users\USER\Desktop\prototype B2B - Modernisation\src",
                Executable = "cmd.exe",
                Arguments = @"/c call ..\venv\Scripts\activate.bat && uvicorn main:app --host 127.0.0.1 --port 8000"
            },
            new ServiceConfig {
                Name = "Interface Web SilaLink",
                Description = "Console Commerciale React/Vite (Port 5173)",
                Port = 5173,
                WorkDir = @"C:\Users\USER\Desktop\prototype B2B - Modernisation\silalink-frontend",
                Executable = "cmd.exe",
                Arguments = "/c npm run dev"
            }
        };

        private Border[] statusPills;
        private TextBlock[] statusTexts;
        private ProgressBar globalProgress;
        private TextBlock globalStatusText;
        private Button btnLaunchApp;
        private Button btnShutdown;

        public MainWindow()
        {
            Title = "SilaLink CRM â€” Control Hub";
            Width = 520;
            Height = 620;
            WindowStartupLocation = WindowStartupLocation.CenterScreen;
            ResizeMode = ResizeMode.NoResize;
            Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#0B0F19"));
            WindowStyle = WindowStyle.SingleBorderWindow;

            BuildUI();
            Loaded += async (s, e) => await StartOrchestrationAsync();
        }

        private void BuildUI()
        {
            var mainGrid = new Grid { Margin = new Thickness(24) };
            mainGrid.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
            mainGrid.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });
            mainGrid.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });

            // 1. Header
            var headerStack = new StackPanel { Margin = new Thickness(0, 0, 0, 24) };
            var lblBrand = new TextBlock
            {
                Text = "SiLaLinK B2B Platform",
                FontSize = 22,
                FontWeight = FontWeights.Bold,
                Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#F8FAFC")),
                FontFamily = new FontFamily("Segoe UI")
            };
            var lblSub = new TextBlock
            {
                Text = "Superviseur de dÃ©ploiement et d'orchestration locale",
                FontSize = 12,
                Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#64748B")),
                Margin = new Thickness(0, 4, 0, 0)
            };
            headerStack.Children.Add(lblBrand);
            headerStack.Children.Add(lblSub);
            Grid.SetRow(headerStack, 0);
            mainGrid.Children.Add(headerStack);

            // 2. Services List
            var serviceStack = new StackPanel();
            statusPills = new Border[services.Length];
            statusTexts = new TextBlock[services.Length];

            for (int i = 0; i < services.Length; i++)
            {
                var card = new Border
                {
                    Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#131B2E")),
                    CornerRadius = new CornerRadius(10),
                    BorderBrush = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#1E293B")),
                    BorderThickness = new Thickness(1),
                    Padding = new Thickness(16),
                    Margin = new Thickness(0, 0, 0, 12)
                };

                var cardGrid = new Grid();
                cardGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
                cardGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });

                var textPanel = new StackPanel();
                var sName = new TextBlock
                {
                    Text = services[i].Name,
                    FontWeight = FontWeights.SemiBold,
                    FontSize = 14,
                    Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#E2E8F0"))
                };
                var sDesc = new TextBlock
                {
                    Text = services[i].Description,
                    FontSize = 11,
                    Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#64748B")),
                    Margin = new Thickness(0, 2, 0, 0)
                };
                textPanel.Children.Add(sName);
                textPanel.Children.Add(sDesc);
                Grid.SetColumn(textPanel, 0);
                cardGrid.Children.Add(textPanel);

                var pill = new Border
                {
                    Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#1E293B")),
                    CornerRadius = new CornerRadius(12),
                    Padding = new Thickness(10, 4, 10, 4),
                    VerticalAlignment = VerticalAlignment.Center
                };
                var pillText = new TextBlock
                {
                    Text = "INITIALISATION",
                    FontSize = 10,
                    FontWeight = FontWeights.Bold,
                    Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#94A3B8"))
                };
                pill.Child = pillText;
                Grid.SetColumn(pill, 1);
                cardGrid.Children.Add(pill);

                statusPills[i] = pill;
                statusTexts[i] = pillText;

                card.Child = cardGrid;
                serviceStack.Children.Add(card);
            }
            Grid.SetRow(serviceStack, 1);
            mainGrid.Children.Add(serviceStack);

            // 3. Footer / Controls
            var footerStack = new StackPanel { Margin = new Thickness(0, 12, 0, 0) };

            globalProgress = new ProgressBar
            {
                Height = 6,
                Maximum = 3,
                Value = 0,
                Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#3B82F6")),
                Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#1E293B")),
                BorderThickness = new Thickness(0),
                Margin = new Thickness(0, 0, 0, 8)
            };
            footerStack.Children.Add(globalProgress);

            globalStatusText = new TextBlock
            {
                Text = "DÃ©marrage des sous-systÃ¨mes en tÃ¢che de fond...",
                FontSize = 11,
                Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#94A3B8")),
                HorizontalAlignment = HorizontalAlignment.Center,
                Margin = new Thickness(0, 0, 0, 16)
            };
            footerStack.Children.Add(globalStatusText);

            btnLaunchApp = new Button
            {
                Content = "Patientez pendant la synchronisation...",
                Height = 44,
                FontSize = 13,
                FontWeight = FontWeights.Bold,
                Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#64748B")),
                Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#1E293B")),
                BorderThickness = new Thickness(0),
                IsEnabled = false,
                Cursor = System.Windows.Input.Cursors.Wait
            };
            btnLaunchApp.Click += (s, e) => {
                Process.Start(new ProcessStartInfo("http://localhost:5173") { UseShellExecute = true });
            };
            footerStack.Children.Add(btnLaunchApp);

            btnShutdown = new Button
            {
                Content = "ArrÃªter tous les services et quitter",
                Height = 32,
                FontSize = 11,
                Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#EF4444")),
                Background = Brushes.Transparent,
                BorderThickness = new Thickness(0),
                Margin = new Thickness(0, 8, 0, 0),
                Cursor = System.Windows.Input.Cursors.Hand
            };
            btnShutdown.Click += (s, e) => {
                KillSilent("node");
                KillSilent("python");
                Application.Current.Shutdown();
            };
            footerStack.Children.Add(btnShutdown);

            Grid.SetRow(footerStack, 2);
            mainGrid.Children.Add(footerStack);

            Content = mainGrid;
        }

        private async Task StartOrchestrationAsync()
        {
            int readyCount = 0;

            for (int i = 0; i < services.Length; i++)
            {
                var svc = services[i];
                globalStatusText.Text = string.Format("DÃ©marrage du service : {0}...", svc.Name);

                if (!IsPortOpen(svc.Port))
                {
                    LaunchSilent(svc.Executable, svc.Arguments, svc.WorkDir);
                }

                // Polling TCP
                bool isUp = false;
                for (int r = 0; r < 40; r++)
                {
                    if (IsPortOpen(svc.Port))
                    {
                        isUp = true;
                        break;
                    }
                    await Task.Delay(1000);
                }

                if (isUp)
                {
                    readyCount++;
                    globalProgress.Value = readyCount;
                    statusPills[i].Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#064E3B"));
                    statusTexts[i].Text = "OPÃ‰RATIONNEL";
                    statusTexts[i].Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#34D399"));
                }
                else
                {
                    statusPills[i].Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#450A0A"));
                    statusTexts[i].Text = "ERREUR TIMEOUT";
                    statusTexts[i].Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#F87171"));
                    globalStatusText.Text = string.Format("Ã‰chec de connexion sur le port {0}.", svc.Port);
                    return;
                }
            }

            // PrÃªt
            globalStatusText.Text = "Tous les micro-services sont actifs et prÃªts.";
            btnLaunchApp.IsEnabled = true;
            btnLaunchApp.Content = "ðŸš€ Ouvrir SilaLink CRM";
            btnLaunchApp.Background = new SolidColorBrush((Color)ColorConverter.ConvertFromString("#2563EB"));
            btnLaunchApp.Foreground = Brushes.White;
            btnLaunchApp.Cursor = System.Windows.Input.Cursors.Hand;
        }

        private bool IsPortOpen(int port)
        {
            try
            {
                using (var client = new TcpClient())
                {
                    var result = client.BeginConnect("127.0.0.1", port, null, null);
                    bool success = result.AsyncWaitHandle.WaitOne(400);
                    if (!success) return false;
                    client.EndConnect(result);
                    return true;
                }
            }
            catch { return false; }
        }

        private void LaunchSilent(string file, string args, string dir)
        {
            try
            {
                var psi = new ProcessStartInfo(file, args)
                {
                    WorkingDirectory = dir,
                    CreateNoWindow = true,
                    UseShellExecute = false,
                    WindowStyle = ProcessWindowStyle.Hidden
                };
                Process.Start(psi);
            }
            catch (Exception ex)
            {
                MessageBox.Show("Erreur au lancement : " + ex.Message);
            }
        }

        private void KillSilent(string processName)
        {
            try
            {
                var psi = new ProcessStartInfo("taskkill", "/F /IM " + processName + ".exe")
                {
                    CreateNoWindow = true,
                    UseShellExecute = false
                };
                using (var p = Process.Start(psi)) { p.WaitForExit(2000); }
            }
            catch { }
        }
    }
}