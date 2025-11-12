$(function () {

    // ****************************************
    //  U T I L I T Y   F U N C T I O N S
    // ****************************************

    const $flash = $("#flash_message");
    const $searchResults = $("#search_results");

    function handleFail(res, fallback) {
        const message = res.responseJSON?.message || res.responseText || fallback || "Server error";
        flashMessage(message);
    }

    function flashMessage(message) {
        $flash.empty();
        if (message) {
            $flash.append(message);
        }
    }

    // Updates the form with data from the response
    function update_form_data(res) {
        $("#promotion_id").val(res.id ?? "");
        $("#promotion_name").val(res.name ?? "");
        $("#promotion_promotion_type").val(res.promotion_type ?? "");
        $("#promotion_value").val(res.value ?? "");
        $("#promotion_product_id").val(res.product_id ?? "");
        $("#promotion_start_date").val(res.start_date ?? "");
        $("#promotion_end_date").val(res.end_date ?? "");
    }

    /// Clears all form fields
    function clear_form_data() {
        $("#promotion_id").val("");
        $("#promotion_name").val("");
        $("#promotion_promotion_type").val("");
        $("#promotion_value").val("");
        $("#promotion_product_id").val("");
        $("#promotion_start_date").val("");
        $("#promotion_end_date").val("");
    }

    function renderPromotionTable(promotions) {
        $searchResults.empty();
        if (!promotions || promotions.length === 0) {
            $searchResults.append("<p>No promotions found.</p>");
            return;
        }

        let table = '<table class="table table-striped" cellpadding="10">';
        table += "<thead><tr>";
        table += '<th class="col-md-2">ID</th>';
        table += '<th class="col-md-2">Name</th>';
        table += '<th class="col-md-2">Type</th>';
        table += '<th class="col-md-2">Value</th>';
        table += '<th class="col-md-2">Product ID</th>';
        table += '<th class="col-md-2">Start Date</th>';
        table += '<th class="col-md-2">End Date</th>';
        table += "</tr></thead><tbody>";

        promotions.forEach((promo, index) => {
            table += `<tr id="row_${index}"><td>${promo.id ?? ""}</td><td>${promo.name ?? ""}</td><td>${promo.promotion_type ?? ""}</td><td>${promo.value ?? ""}</td><td>${promo.product_id ?? ""}</td><td>${promo.start_date ?? ""}</td><td>${promo.end_date ?? ""}</td></tr>`;
        });

        table += "</tbody></table>";
        $searchResults.append(table);
        if (promotions.length > 0) {
            update_form_data(promotions[0]);
        }
    }

    // ****************************************
    // Create a Promotion
    // ****************************************

    $("#create_promotion-btn").click(function () {
        const payload = {
            name: $("#promotion_name").val(),
            promotion_type: $("#promotion_promotion_type").val(),
            value: parseInt($("#promotion_value").val()),
            product_id: parseInt($("#promotion_product_id").val()),
            start_date: $("#promotion_start_date").val(),
            end_date: $("#promotion_end_date").val()
        };

        if (!payload.name || !payload.promotion_type) {
            flashMessage("Name and Promotion Type are required to create a promotion");
            return;
        }

        flashMessage("");

        $.ajax({
            type: "POST",
            url: "/promotions",
            contentType: "application/json",
            data: JSON.stringify(payload),
        })
            .done(function (res) {
                update_form_data(res);
                renderPromotionTable([res]);
                flashMessage("Success");
            })
            .fail(function (res) {
                handleFail(res, "Failed to create promotion");
            });
    });


    // ****************************************
    // Update a Promotion
    // ****************************************

    // $("#update_promotion-btn").click(function () {

    //     let promotion_id = $("#promotion_id").val();
    //     let name = $("#promotion_name").val();
    //     let type = $("#promotion_promotion_type").val();
    //     let value = $("#promotion_value").val();
    //     let product_id = $("#promotion_product_id").val();
    //     let start_date = $("#promotion_start_date").val();
    //     let end_date = $("#promotion_end_date").val();

    //     let data = {
    //         "name": name,
    //         "promotion_type": type,
    //         "value": parseInt(value),
    //         "product_id": parseInt(product_id),
    //         "start_date": start_date,
    //         "end_date": end_date
    //     };

    //     $("#flash_message").empty();

    //     let ajax = $.ajax({
    //             type: "PUT",
    //             url: `/promotions/${promotion_id}`,
    //             contentType: "application/json",
    //             data: JSON.stringify(data)
    //         })

    //     ajax.done(function(res){
    //         update_form_data(res)
    //         flash_message("Success")
    //     });

    //     ajax.fail(function(res){
    //         flash_message(res.responseJSON.message)
    //     });

    // });

    // ****************************************
    // Retrieve a Promotion
    // ****************************************

    // $("#retrieve_promotion-btn").click(function () {

    //     let promotion_id = $("#promotion_id").val();

    //     $("#flash_message").empty();

    //     let ajax = $.ajax({
    //         type: "GET",
    //         url: `/promotions/${promotion_id}`,
    //         contentType: "application/json",
    //         data: ''
    //     })

    //     ajax.done(function(res){
    //         update_form_data(res)
    //         flash_message("Success")
    //     });

    //     ajax.fail(function(res){
    //         clear_form_data()
    //         flash_message(res.responseJSON.message)
    //     });

    // });

    // ****************************************
    // Delete a Promotion
    // ****************************************

    $("#delete-btn").click(function () {

        let promotion_id = $("#promotion_id").val();

        $("#flash_message").empty();

        let ajax = $.ajax({
            type: "DELETE",
            url: `/promotions/${promotion_id}`,
            contentType: "application/json",
            data: '',
        })

        ajax.done(function(res){
            clear_form_data()
            flashMessage("Promotion has been Deleted!")
        });

        ajax.fail(function(res){
            handleFail(res, "Server error!")
        });
    });

    // ****************************************
    // Clear the form
    // ****************************************

    // $("#clear_form_fields-btn").click(function () {
    //     $("#promotion_id").val("");
    //     $("#flash_message").empty();
    //     clear_form_data()
    // });

    // ****************************************
    // Search for a Promotion
    // ****************************************

    // $("#search_promotions-btn").click(function () {

    //     let name = $("#promotion_search_name").val();
    //     let product_id = $("#promotion_search_product").val();
    //     let promotion_type = $("#promotion_search_type").val();

    //     let queryString = ""

    //     if (name) {
    //         queryString += 'name=' + name
    //     }
    //     if (product_id) {
    //         if (queryString.length > 0) {
    //             queryString += '&product_id=' + product_id
    //         } else {
    //             queryString += 'product_id=' + product_id
    //         }
    //     }
    //     if (promotion_type) {
    //         if (queryString.length > 0) {
    //             queryString += '&promotion_type=' + promotion_type
    //         } else {
    //             queryString += 'promotion_type=' + promotion_type
    //         }
    //     }

    //     $("#flash_message").empty();

    //     let ajax = $.ajax({
    //         type: "GET",
    //         url: `/promotions?${queryString}`,
    //         contentType: "application/json",
    //         data: ''
    //     })

    //     ajax.done(function(res){
    //         $("#search_results").empty();
    //         let table = '<table class="table table-striped" cellpadding="10">'
    //         table += '<thead><tr>'
    //         table += '<th class="col-md-2">ID</th>'
    //         table += '<th class="col-md-2">Name</th>'
    //         table += '<th class="col-md-2">Type</th>'
    //         table += '<th class="col-md-2">Value</th>'
    //         table += '<th class="col-md-2">Product ID</th>'
    //         table += '<th class="col-md-2">Start Date</th>'
    //         table += '<th class="col-md-2">End Date</th>'
    //         table += '</tr></thead><tbody>'
    //         let firstPromotion = "";
    //         for(let i = 0; i < res.length; i++) {
    //             let promotion = res[i];
    //             table +=  `<tr id="row_${i}"><td>${promotion.id}</td><td>${promotion.name}</td><td>${promotion.promotion_type}</td><td>${promotion.value}</td><td>${promotion.product_id}</td><td>${promotion.start_date}</td><td>${promotion.end_date}</td></tr>`;
    //             if (i == 0) {
    //                 firstPromotion = promotion;
    //             }
    //         }
    //         table += '</tbody></table>';
    //         $("#search_results").append(table);

    //         // copy the first result to the form
    //         if (firstPromotion != "") {
    //             update_form_data(firstPromotion)
    //         }

    //         flash_message("Success")
    //     });

    //     ajax.fail(function(res){
    //         flash_message(res.responseJSON.message)
    //     });

    // });

    // ****************************************
    // List All Promotions
    // ****************************************

    // $("#list_promotions-btn").click(function () {

    //     $("#flash_message").empty();

    //     let ajax = $.ajax({
    //         type: "GET",
    //         url: "/promotions",
    //         contentType: "application/json",
    //         data: ''
    //     })

    //     ajax.done(function(res){
    //         $("#search_results").empty();
    //         let table = '<table class="table table-striped" cellpadding="10">'
    //         table += '<thead><tr>'
    //         table += '<th class="col-md-2">ID</th>'
    //         table += '<th class="col-md-2">Name</th>'
    //         table += '<th class="col-md-2">Type</th>'
    //         table += '<th class="col-md-2">Value</th>'
    //         table += '<th class="col-md-2">Product ID</th>'
    //         table += '<th class="col-md-2">Start Date</th>'
    //         table += '<th class="col-md-2">End Date</th>'
    //         table += '</tr></thead><tbody>'
    //         let firstPromotion = "";
    //         for(let i = 0; i < res.length; i++) {
    //             let promotion = res[i];
    //             table +=  `<tr id="row_${i}"><td>${promotion.id}</td><td>${promotion.name}</td><td>${promotion.promotion_type}</td><td>${promotion.value}</td><td>${promotion.product_id}</td><td>${promotion.start_date}</td><td>${promotion.end_date}</td></tr>`;
    //             if (i == 0) {
    //                 firstPromotion = promotion;
    //             }
    //         }
    //         table += '</tbody></table>';
    //         $("#search_results").append(table);

    //         // copy the first result to the form
    //         if (firstPromotion != "") {
    //             update_form_data(firstPromotion)
    //         }

    //         flash_message("Success")
    //     });

    //     ajax.fail(function(res){
    //         flash_message(res.responseJSON.message)
    //     });

    // });

    // ****************************************
    // Deactivate a Promotion (ACTION)
    // ****************************************

    // $("#deactivate_promotion-btn").click(function () {

    //     let promotion_id = $("#promotion_action_id").val();

    //     $("#flash_message").empty();

    //     let ajax = $.ajax({
    //         type: "PUT",
    //         url: `/promotions/${promotion_id}/deactivate`,
    //         contentType: "application/json",
    //         data: ''
    //     })

    //     ajax.done(function(res){
    //         update_form_data(res)
    //         flash_message("Promotion has been deactivated!")
    //     });

    //     ajax.fail(function(res){
    //         flash_message(res.responseJSON.message)
    //     });

    // });

})
