function convert_to_mgl(do_input, t, p, s){
    //do: dissolved oxygen in percent saturation
    //t: temperature in celcius
    //p: pressure in hPa
    //s: salinity in parts per thousand
 
    const T = t + 273.15; //temperature in kelvin
    const P = p * 9.869233e-4; //pressure in atm

    const DO_baseline = Math.exp(-139.34411 + 1.575701e5/T - 6.642308e7/Math.pow(T, 2) + 1.2438e10/Math.pow(T, 3) - 8.621949e11/Math.pow(T, 4));

    const Fs = Math.exp(-s * (0.017674 - 10.754/T + 2140.7/Math.pow(T, 2)));

    const theta = 0.000975 - 1.426e-5 * t + 6.436e-8 * Math.pow(t, 2);
    const u = Math.exp(11.8571 - 3840.7/T - 216961/Math.pow(T, 2));
    const Fp = (P - u) * (1 - theta * P) / (1 - u) / (1 - theta);

    const DO_corrected = DO_baseline * Fs * Fp;
    const DO_mgl = do_input / 100 * DO_corrected;

    return DO_mgl;
}

function get_start_time(delta) {
    var start = new Date();
    start.setHours(start.getHours() - delta);
    let year = start.getUTCFullYear();
    let month = start.getUTCMonth() + 1;
    if (month < 10)
        month = "0" + month;
    let day = start.getUTCDate();
    if (day < 10)
        day = "0" + day;
    let hour = start.getUTCHours();
    if (hour < 10)
        hour = "0" + hour;
    let minute = start.getUTCMinutes();
    if (minute < 10)
        minute = "0" + minute;
    let startString = '' + year + month + day + '_' + hour + ':' + minute + ':00';
    return startString;
};
