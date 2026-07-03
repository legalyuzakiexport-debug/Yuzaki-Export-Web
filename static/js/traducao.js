const translations = {
    'pt': {
        // Login
        'titulo': 'Entrar',
        'email': 'O teu email',
        'senha': 'A tua senha',
        'esqueci': 'Esqueci minha senha',
        'entrar': 'Entrar',
        'nao_tem_conta': 'Não tem conta?',
        'crie_aqui': 'Crie uma aqui',
        'motores': 'A preparar motores de exportação...',
        // Dashboard (Exemplos)
        'bem_vindo': 'Bem-vindo ao Painel',
        'sair': 'Sair',
        'tabela_data': 'Data',
        'tabela_destino': 'Destino'
    },
    'en': {
        'titulo': 'Login',
        'email': 'Your email',
        'senha': 'Your password',
        'esqueci': 'Forgot password',
        'entrar': 'Sign In',
        'nao_tem_conta': "Don't have an account?",
        'crie_aqui': 'Create one here',
        'motores': 'Preparing engines...',
        'bem_vindo': 'Welcome to Dashboard',
        'sair': 'Logout',
        'tabela_data': 'Date',
        'tabela_destino': 'Destination'
    },
    'es': {
        'titulo': 'Entrar',
        'email': 'Tu correo',
        'senha': 'Tu contraseña',
        'esqueci': 'Olvidé mi contraseña',
        'entrar': 'Entrar',
        'nao_tem_conta': '¿No tienes cuenta?',
        'crie_aqui': 'Crea una aquí',
        'motores': 'Preparando motores...',
        'bem_vindo': 'Bienvenido al Panel',
        'sair': 'Salir',
        'tabela_data': 'Fecha',
        'tabela_destino': 'Destino'
    },
    'jp': {
        'titulo': 'ログイン',
        'email': 'メールアドレス',
        'senha': 'パスワード',
        'esqueci': 'パスワードを忘れた',
        'entrar': 'ログイン',
        'nao_tem_conta': 'アカウントをお持ちではありませんか？',
        'crie_aqui': 'こちらで作成',
        'motores': '準備中...',
        'bem_vindo': 'ダッシュボードへようこそ',
        'sair': 'ログアウト',
        'tabela_data': '日付',
        'tabela_destino': '先'
    }
};

// FUNÇÃO PRINCIPAL: Aplica a tradução em qualquer página
function applyTranslation(lang) {
    const t = translations[lang];
    if (!t) return;

    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (t[key]) {
            if (el.tagName === 'INPUT') {
                el.placeholder = t[key];
            } else {
                el.innerText = t[key];
            }
        }
    });

    // MEMÓRIA: Guarda a língua no navegador
    localStorage.setItem('selectedLanguage', lang);
}

// Quando clicas na bandeira
function changeLanguage(lang, flagUrl, langText) {
    applyTranslation(lang);
    
    // Atualiza o botão visual (se ele existir na página)
    const btnFlag = document.getElementById('current-lang-flag');
    const btnText = document.getElementById('current-lang-text');
    if (btnFlag) btnFlag.src = flagUrl;
    if (btnText) btnText.innerText = langText;
}

// MAL A PÁGINA ABRE: Verifica a memória e traduz tudo instantaneamente
document.addEventListener('DOMContentLoaded', () => {
    const savedLang = localStorage.getItem('selectedLanguage') || 'pt';
    applyTranslation(savedLang);

    // Se a página tiver o seletor, põe a bandeira certa no botão
    const btnFlag = document.getElementById('current-lang-flag');
    if (btnFlag) {
        const flags = {
            'pt': 'https://flagcdn.com/w20/pt.png',
            'en': 'https://flagcdn.com/w20/gb.png',
            'es': 'https://flagcdn.com/w20/es.png',
            'jp': 'https://flagcdn.com/w20/jp.png'
        };
        btnFlag.src = flags[savedLang];
        document.getElementById('current-lang-text').innerText = savedLang.toUpperCase();
    }
}); 