// 员工绩效管理系统 - 主应用程序JS

// 初始化应用
document.addEventListener('DOMContentLoaded', function() {
    // 初始化工具提示
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // 自动关闭警告框
    setTimeout(function() {
        var alerts = document.querySelectorAll('.alert-dismissible');
        alerts.forEach(function(alert) {
            var closeBtn = alert.querySelector('.btn-close');
            if (closeBtn) {
                closeBtn.click();
            }
        });
    }, 5000);

    // 表格行点击效果
    var tableRows = document.querySelectorAll('table tbody tr');
    tableRows.forEach(function(row) {
        row.addEventListener('click', function(e) {
            if (!e.target.closest('button') && !e.target.closest('a')) {
                this.classList.toggle('table-active');
            }
        });
    });
});

// 工具函数
const Utils = {
    // 显示加载动画
    showLoading: function(element) {
        if (element) {
            element.innerHTML = `
                <div class="d-flex justify-content-center">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">加载中...</span>
                    </div>
                </div>
            `;
        }
    },

    // 格式化日期
    formatDate: function(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit'
        });
    },

    // 显示通知
    showNotification: function(message, type = 'info') {
        const alert = document.createElement('div');
        alert.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        alert.style.top = '20px';
        alert.style.right = '20px';
        alert.style.zIndex = '9999';
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        document.body.appendChild(alert);

        // 自动移除
        setTimeout(function() {
            alert.remove();
        }, 5000);
    },

    // 确认对话框
    confirm: function(message, callback) {
        if (confirm(message)) {
            callback();
        }
    }
};

// 模板相关功能
const TemplateManager = {
    // 验证变量格式
    validateVariables: function(variablesStr) {
        try {
            if (variablesStr.startsWith('pickle:')) {
                // 对于序列化数据，进行基本的base64验证
                const encoded = variablesStr.substring(7);
                atob(encoded); // 尝试解码base64
                return true;
            } else {
                JSON.parse(variablesStr);
                return true;
            }
        } catch (e) {
            return false;
        }
    },

    // 格式化JSON
    formatJSON: function(jsonStr) {
        try {
            const obj = JSON.parse(jsonStr);
            return JSON.stringify(obj, null, 2);
        } catch (e) {
            return jsonStr;
        }
    }
};

// 全局错误处理
window.addEventListener('error', function(e) {
    console.error('应用程序错误:', e.error);
    Utils.showNotification('系统发生错误，请刷新页面重试', 'danger');
});

// 网络请求错误处理
window.addEventListener('unhandledrejection', function(e) {
    console.error('网络请求错误:', e.reason);
    Utils.showNotification('网络请求失败，请检查网络连接', 'warning');
}); 