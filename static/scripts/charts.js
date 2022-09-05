var chart = LightweightCharts.createChart(document.querySelector('.chart'), {
  height: 350,
	layout: {
		backgroundColor: '#000000',
		textColor: 'rgba(255, 255, 255, 0.9)',
	},
	grid: {
		vertLines: {
			color: 'rgba(197, 203, 206, 0.5)',
		},
		horzLines: {
			color: 'rgba(197, 203, 206, 0.5)',
		},
	},
	crosshair: {
		mode: LightweightCharts.CrosshairMode.Normal,
	},
	rightPriceScale: {
		borderColor: 'rgba(197, 203, 206, 0.8)',
	},
	timeScale: {
		borderColor: 'rgba(197, 203, 206, 0.8)',
	},
});

var candleSeries = chart.addCandlestickSeries({
  upColor: 'rgba(0, 255, 0, 1)',
  downColor: 'rgba(255, 0, 0, 1)',
  borderDownColor: 'rgba(255, 0, 0, 1)',
  borderUpColor: 'rgba(0, 255, 0, 1)',
  wickDownColor: 'rgba(255, 0, 0, 1)',
  wickUpColor: 'rgba(0, 255, 0, 1)',
});


fetch('https://cryptomassideation.herokuapp.com/crypto_analysis_api/fetch_data')
    .then((r)=>r.json())
    .then((response)=>{

		console.log(response)

		candleSeries.setData(response['candlesticks'])

		candleSeries.setMarkers(response['buysell']);
		
    })


// fetch('http://0.0.0.0:5000/fetch_data')
//     .then((r)=>r.json())
//     .then((response)=>{

// 		console.log(response)

// 		candleSeries.setData(response['candlesticks'])

// 		candleSeries.setMarkers(response['buysell']);
		
//     })


