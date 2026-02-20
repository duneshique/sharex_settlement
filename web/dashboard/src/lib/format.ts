export function formatCurrency(value: number): string {
    return new Intl.NumberFormat('ko-KR', {
        style: 'currency',
        currency: 'KRW',
    }).format(value);
}

export function formatNumber(value: number): string {
    return new Intl.NumberFormat('ko-KR').format(value);
}

export function formatPercent(value: number): string {
    return `${(value * 100).toFixed(1)}%`;
}
