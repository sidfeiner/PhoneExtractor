CREATE view facebook.infos_to_del_v AS (SELECT b.id AS id_delete FROM
    facebook.user_infos a
        INNER JOIN
    facebook.user_infos b ON a.user_id = b.user_id
        AND a.post_id = b.post_id
        AND a.info_kind = b.info_kind
        AND a.canonized_info = b.canonized_info
        AND b.id > a.id)
;
DELETE FROM user_infos 
WHERE
    EXISTS( SELECT 
        *
    FROM
        infos_to_del
    
    WHERE
        user_infos.id = infos_to_del.id_delete);