$(function(){
    $('#user_name').qtip({
        content: {
            text: function() {
                var template = Handlebars.compile($("#userbox_template").html());
                return template();
            }
        },
        show: {
            event: 'click'
        },
        hide: {
            event: 'unfocus'
        },
        style: {
            classes: 'ui-tooltip-jtools ui-tooltip-shadow ui-tooltip-rounded'
        },
        position: {
            my: 'top right',
            at: 'bottom center'
        }
    });
});
