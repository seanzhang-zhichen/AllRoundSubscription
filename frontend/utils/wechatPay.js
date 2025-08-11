/**
 * 微信支付工具
 */

export async function payInMiniProgram(params) {
  return new Promise((resolve, reject) => {
    try {
      // #ifdef MP-WEIXIN
      wx.requestPayment({
        timeStamp: params.timeStamp,
        nonceStr: params.nonceStr,
        package: params.package,
        signType: params.signType || 'RSA',
        paySign: params.paySign,
        success: (res) => resolve(res),
        fail: (err) => reject(err)
      })
      // #endif

      // #ifndef MP-WEIXIN
      reject(new Error('当前非微信小程序环境，无法发起小程序支付'))
      // #endif
    } catch (e) {
      reject(e)
    }
  })
}

export function redirectToH5Pay(h5Url) {
  // #ifdef H5
  window.location.href = h5Url
  // #endif
  // #ifndef H5
  uni.navigateTo({ url: `/pages/webview/webview?url=${encodeURIComponent(h5Url)}` })
  // #endif
} 